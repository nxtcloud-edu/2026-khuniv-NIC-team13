package com.example.demo.metrics.aop;

import com.example.demo.email.api.v2.auth.dto.EmailVerificationSendRequest;
import com.example.demo.metrics.app.MetricsService;
import lombok.RequiredArgsConstructor;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

/**
 * metrics 집계를 위한 AOP.
 *
 * 실패 포함 카운트를 위해 controller 진입 시점에 실행되도록 Order를 가장 앞에 둡니다.
 */
@Aspect
@Order(0)
@Component
@RequiredArgsConstructor
public class MetricsAspect {

    private final MetricsService metricsService;

    @Around("execution(* com.example.demo.email.api.v2.auth.controller.EmailAuthV2Controller.sendVerification(..))")
    public Object recordSendVerifyEmail(ProceedingJoinPoint pjp) throws Throwable {
        String email = null;
        try {
            Object[] args = pjp.getArgs();
            if (args != null && args.length > 0 && args[0] instanceof EmailVerificationSendRequest request) {
                email = request.getEmail();
            }
        } catch (Exception ignored) {
            // metrics는 본 로직을 깨지 않도록 무시
        }

        metricsService.recordSendVerifyEmailAttempt(email);
        return pjp.proceed();
    }
}
