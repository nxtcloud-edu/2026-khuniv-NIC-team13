package com.example.demo.session.api.v2.controller;

import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.shared.web.v2.response.SuccessCode;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import com.example.demo.session.api.v2.app.V2SessionService;
import com.example.demo.session.api.v2.dto.SessionExtendData;
import com.example.demo.session.api.v2.dto.SessionStartData;
import com.example.demo.session.api.v2.dto.SessionStartRequest;
import com.example.demo.config.PertineoSessionProperties;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.time.Instant;

@RestController
@RequestMapping(value = "/api/sessions", headers = V2ApiHeaders.MAPPING_CONDITION)
@RequiredArgsConstructor
@Tag(name = "Sessions V2", description = "세션 시작/연장 (쿠키 기반)")
public class V2SessionController {

    private final V2SessionService sessionService;
    private final PertineoSessionProperties sessionProperties;

    @PostMapping("/start")
    @Operation(summary = "세션 시작", description = "이메일 인증 및 약관 동의 후 세션 쿠키를 발급합니다.")
    public ResponseEntity<SuccessResponse<SessionStartData>> start(@Valid @RequestBody SessionStartRequest request) {
        V2SessionService.StartResult result = sessionService.start(request);

        Instant expiresAt = Instant.parse(result.data().getExpiresAt());
        long maxAgeSeconds = Math.max(0L, Duration.between(Instant.now(), expiresAt).getSeconds());

        ResponseCookie cookie = ResponseCookie.from(sessionProperties.getCookieName(), result.sessionId())
                .httpOnly(true)
                .secure(sessionProperties.isSecure())
                .path(sessionProperties.getCookiePath())
                .sameSite(sessionProperties.getSameSite())
                .maxAge(Duration.ofSeconds(maxAgeSeconds))
                .build();

        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, cookie.toString())
                .body(SuccessResponse.of(SuccessCode.SUCCESS, result.data()));
    }

    @PostMapping("/extend")
    @Operation(summary = "세션 연장", description = "세션 쿠키로 현재 세션을 찾고 만료 시간을 연장합니다.")
    @Parameter(in = ParameterIn.COOKIE, name = "PERTINEO_SESSION", required = true, description = "세션 쿠키(기본값). 실제 이름은 환경설정에 따릅니다.")
    public ResponseEntity<SuccessResponse<SessionExtendData>> extend(
            HttpServletRequest servletRequest
    ) {
        String sessionId = readSessionIdFromCookie(servletRequest, sessionProperties.getCookieName());
        V2SessionService.ExtendResult result = sessionService.extend(sessionId);

        long maxAgeSeconds = Math.max(0L, Duration.between(Instant.now(), result.expiresAt()).getSeconds());
        ResponseCookie cookie = ResponseCookie.from(sessionProperties.getCookieName(), sessionId)
                .httpOnly(true)
                .secure(sessionProperties.isSecure())
                .path(sessionProperties.getCookiePath())
                .sameSite(sessionProperties.getSameSite())
                .maxAge(Duration.ofSeconds(maxAgeSeconds))
                .build();

        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, cookie.toString())
                .body(SuccessResponse.of(SuccessCode.SUCCESS, result.data()));
    }

    private static String readSessionIdFromCookie(HttpServletRequest request, String cookieName) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        for (Cookie cookie : cookies) {
            if (cookieName.equals(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return null;
    }
}

