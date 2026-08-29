package com.example.demo.email.api.v2.auth.controller;

import com.example.demo.email.api.v2.auth.app.EmailAuthV2Service;
import com.example.demo.email.api.v2.auth.dto.EmailVerificationSendRequest;
import com.example.demo.email.api.v2.auth.dto.EmailVerifyRequest;
import com.example.demo.email.api.v2.auth.dto.EmailVerifyResponseData;
import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.shared.web.v2.response.SuccessCode;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import com.example.demo.email.app.EmailVerificationThrottle;
import com.example.demo.email.app.EmailService;
import com.example.demo.email.domain.Email;
import com.example.demo.shared.security.MemberGuard;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping(value = "/api/auth/email", headers = V2ApiHeaders.MAPPING_CONDITION)
@RequiredArgsConstructor
@Tag(name = "Auth Email V2", description = "이메일 인증번호 발송·확인 (v2)")
public class EmailAuthV2Controller {

    private final EmailService emailService;
    private final EmailAuthV2Service emailAuthV2Service;
    private final MemberGuard memberGuard;
    private final EmailVerificationThrottle emailVerificationThrottle;

    @PostMapping("/verification")
    @Operation(summary = "인증번호 발송", description = "이메일로 인증번호를 발송합니다.")
    public ResponseEntity<SuccessResponse<Void>> sendVerification(@Valid @RequestBody EmailVerificationSendRequest request) {
        String email = normalizeEmail(request.getEmail());
        memberGuard.requireMember(email);
        emailVerificationThrottle.requireUnderThreshold(email);
        emailService.sendVerificationEmail(email);
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, "인증 번호 발송", null));
    }

    @PostMapping("/verify")
    @Operation(summary = "인증번호 확인", description = "인증번호를 확인하고 이메일 검증을 완료합니다.")
    public ResponseEntity<SuccessResponse<EmailVerifyResponseData>> verify(@Valid @RequestBody EmailVerifyRequest request) {
        String email = normalizeEmail(request.getEmail());
        memberGuard.requireMember(email);
        EmailVerifyResponseData data = emailAuthV2Service.verifyCode(email, request.getCode());
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, data));
    }

    @GetMapping("/credit")
    @Operation(summary = "크레딧 정보 확인", description = "남은 횟수가 몇번인지 확인합니다.")
    public ResponseEntity<SuccessResponse<Email>> getCredit(@Valid @RequestParam String email) {

        Email emailEntity = emailService.getEmailEntity(normalizeEmail(email));
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, emailEntity));
    }

    private static String normalizeEmail(String email) {
        return email == null ? null : email.trim().toLowerCase();
    }
}
