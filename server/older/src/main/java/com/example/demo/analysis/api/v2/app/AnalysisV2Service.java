package com.example.demo.analysis.api.v2.app;

import com.example.demo.analysis.api.v2.dto.AnalysisV2RequestDto;
import com.example.demo.email.domain.Email;
import com.example.demo.email.infra.EmailRepository;
import com.example.demo.shared.dynamodb.handler.AccessCodeHandler;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.Disposable;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisV2Service {

    private final WebClient webClient = WebClient.create();
    @Value("${analysis.service.base-url}")
    private String analysisServiceBaseUrl;
    private final AccessCodeHandler accessCodeHandler;
    private final EmailRepository emailRepository;

    public SseEmitter connect(AnalysisV2RequestDto analysisV2RequestDto) {

        SseEmitter emitter = new SseEmitter(1000L * 60 * 5); // 5분
        AtomicBoolean streamTerminated = new AtomicBoolean(false);
        AtomicBoolean finalStateHandled = new AtomicBoolean(false);
        AtomicReference<Disposable> subscriptionRef = new AtomicReference<>();
        String userId = analysisV2RequestDto.getUserId();
        String apiUrl = analysisServiceBaseUrl + "/api/agent/analyze/stream";

        emitter.onCompletion(() -> cleanupStream(streamTerminated, subscriptionRef));
        emitter.onTimeout(() -> {
            log.info("SSE 타임아웃으로 스트림 종료: {}", userId);
            cleanupStream(streamTerminated, subscriptionRef);
            safeComplete(emitter);
        });
        emitter.onError(error -> {
            if (isExpectedDisconnect(error)) {
                log.info("SSE client disconnect 감지: {}", userId);
            } else {
                log.warn("SSE emitter 에러: {}", error.getMessage());
            }
            cleanupStream(streamTerminated, subscriptionRef);
        });

        Disposable subscription = webClient.post()
                .uri(apiUrl)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(analysisV2RequestDto)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .retrieve()
                .bodyToFlux(JsonNode.class)
                .subscribe(
                        jsonNode -> {
                            if (streamTerminated.get()) {
                                return;
                            }

                            try {
                                emitter.send(SseEmitter.event().data(jsonNode.toString(), MediaType.APPLICATION_JSON));

                                if (isFinalState(jsonNode) && finalStateHandled.compareAndSet(false, true)) {
                                    Email email = emailRepository.findByEmail(userId);
                                    if (email != null) {
                                        email.setCount(email.getCount() + 1);
                                        emailRepository.save(email);
                                    } else {
                                        log.warn("final_state 수신했지만 Email 엔티티 없음: {}", userId);
                                    }
                                }
                            } catch (IOException | IllegalStateException e) {
                                handleSendFailure(emitter, streamTerminated, subscriptionRef, userId, e);
                            }
                        },
                        error -> {
                            if (streamTerminated.get()) {
                                return;
                            }

                            if (isExpectedDisconnect(error)) {
                                log.info("disconnect 이후 upstream 정리 완료: {}", userId);
                                cleanupStream(streamTerminated, subscriptionRef);
                                safeComplete(emitter);
                                return;
                            }

                            log.error("외부 스트림 에러: {}", error.getMessage());
                            cleanupStream(streamTerminated, subscriptionRef);
                            safeCompleteWithError(emitter, error);
                        },
                        () -> {
                            if (streamTerminated.get()) {
                                return;
                            }

                            log.info("외부 스트림 종료");
                            cleanupStream(streamTerminated, subscriptionRef);
                            safeComplete(emitter);
                        }
                );
        subscriptionRef.set(subscription);

        if (streamTerminated.get()) {
            subscription.dispose();
        }

        accessCodeHandler.deleteAccessCode(userId);
        return emitter;
    }

    private void handleSendFailure(SseEmitter emitter,
                                   AtomicBoolean streamTerminated,
                                   AtomicReference<Disposable> subscriptionRef,
                                   String userId,
                                   Exception exception) {
        if (isExpectedDisconnect(exception)) {
            log.info("SSE client disconnect 로 전송 중단: {}", userId);
        } else {
            log.error("SSE 전송 실패: {}", exception.getMessage());
        }

        cleanupStream(streamTerminated, subscriptionRef);
        safeComplete(emitter);
    }

    private void cleanupStream(AtomicBoolean streamTerminated,
                               AtomicReference<Disposable> subscriptionRef) {
        if (!streamTerminated.compareAndSet(false, true)) {
            return;
        }

        Disposable subscription = subscriptionRef.getAndSet(null);
        if (subscription != null && !subscription.isDisposed()) {
            subscription.dispose();
        }
    }

    private boolean isFinalState(JsonNode jsonNode) {
        return jsonNode.has("type") && "final_state".equals(jsonNode.get("type").asText());
    }

    private boolean isExpectedDisconnect(Throwable throwable) {
        String className = throwable.getClass().getName();
        String message = throwable.getMessage();

        if (className.contains("ClientAbortException") || className.contains("AsyncRequestNotUsableException")) {
            return true;
        }

        return message != null && (
                message.contains("Broken pipe")
                        || message.contains("ResponseBodyEmitter has already completed")
                        || message.contains("Response not usable after response errors.")
        );
    }

    private void safeComplete(SseEmitter emitter) {
        try {
            emitter.complete();
        } catch (IllegalStateException ignored) {
            // 이미 종료된 emitter는 조용히 무시
        }
    }

    private void safeCompleteWithError(SseEmitter emitter, Throwable error) {
        try {
            emitter.completeWithError(error);
        } catch (IllegalStateException ignored) {
            // 이미 종료된 emitter는 조용히 무시
        }
    }
}
