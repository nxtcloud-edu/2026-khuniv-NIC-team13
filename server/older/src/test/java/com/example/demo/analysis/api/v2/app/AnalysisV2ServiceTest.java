package com.example.demo.analysis.api.v2.app;

import com.example.demo.analysis.api.v2.dto.AnalysisV2RequestDto;
import com.example.demo.email.infra.EmailRepository;
import com.example.demo.shared.dynamodb.handler.AccessCodeHandler;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

class AnalysisV2ServiceTest {

    private HttpServer httpServer;
    private CountDownLatch requestReceived;
    private AtomicReference<String> requestPath;

    @BeforeEach
    void setUp() throws IOException {
        requestReceived = new CountDownLatch(1);
        requestPath = new AtomicReference<>();
        httpServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        httpServer.createContext("/", exchange -> {
            requestPath.set(exchange.getRequestURI().getPath());
            requestReceived.countDown();

            byte[] responseBody = "{}".getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(500, responseBody.length);

            try (OutputStream outputStream = exchange.getResponseBody()) {
                outputStream.write(responseBody);
            }
        });
        httpServer.start();
    }

    @AfterEach
    void tearDown() {
        httpServer.stop(0);
    }

    @Test
    void connectUsesAnalysisServiceBaseUrlForOutboundRequest() throws Exception {
        AccessCodeHandler accessCodeHandler = mock(AccessCodeHandler.class);
        EmailRepository emailRepository = mock(EmailRepository.class);
        AnalysisV2Service analysisV2Service = new AnalysisV2Service(accessCodeHandler, emailRepository);
        ReflectionTestUtils.setField(
                analysisV2Service,
                "analysisServiceBaseUrl",
                "http://127.0.0.1:" + httpServer.getAddress().getPort()
        );

        AnalysisV2RequestDto requestDto = new AnalysisV2RequestDto();
        requestDto.setUserId("student@khu.ac.kr");

        SseEmitter emitter = analysisV2Service.connect(requestDto);

        assertNotNull(emitter);
        assertTrue(requestReceived.await(5, TimeUnit.SECONDS));
        assertEquals("/api/agent/analyze/stream", requestPath.get());
        verify(accessCodeHandler).deleteAccessCode("student@khu.ac.kr");
        verifyNoInteractions(emailRepository);
    }
}
