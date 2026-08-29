package com.example.demo.shared.web.v2;

import com.example.demo.analysis.exception.AnalysisCountExceedException;
import com.example.demo.shared.web.v2.response.ErrorCode;
import com.example.demo.shared.web.v2.response.ErrorResponse;
import com.example.demo.session.api.v2.exception.AgreementRequiredException;
import com.example.demo.shared.exception.EmailNotVerifiedException;
import com.example.demo.session.api.v2.exception.InvalidSessionException;
import com.example.demo.session.api.v2.exception.SessionExpiredException;
import com.example.demo.email.exception.AccessCodeCountException;
import com.example.demo.email.exception.EmailSendFailException;
import com.example.demo.shared.exception.AccessCodeExpiredException;
import com.example.demo.shared.exception.AccessCodeMismatchException;
import com.example.demo.shared.exception.NotMemberException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice(basePackages = {
        "com.example.demo.analysis.api.v2",
        "com.example.demo.autocomplete.api.v2",
        "com.example.demo.email.api.v2",
        "com.example.demo.notice.api.v2",
        "com.example.demo.parsing.api.v2",
        "com.example.demo.session.api.v2"
})
public class V2ApiExceptionHandler {

    @ExceptionHandler(AccessCodeMismatchException.class)
    public ResponseEntity<ErrorResponse> handleAccessCodeMismatch(AccessCodeMismatchException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of(ErrorCode.INVALID_ACCESS_CODE, ex.getMessage()));
    }

    @ExceptionHandler(AccessCodeExpiredException.class)
    public ResponseEntity<ErrorResponse> handleAccessCodeExpired(AccessCodeExpiredException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of(ErrorCode.ACCESS_CODE_EXPIRED, ex.getMessage()));
    }

    @ExceptionHandler(NotMemberException.class)
    public ResponseEntity<ErrorResponse> handleNotMember(NotMemberException ex) {
        return ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(ErrorResponse.of(ErrorCode.NOT_AUTHENTICATED, ex.getMessage()));
    }

    @ExceptionHandler(EmailSendFailException.class)
    public ResponseEntity<ErrorResponse> handleEmailSendFail(EmailSendFailException ex) {
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse.of(ErrorCode.EMAIL_SEND_FAILED, ex.getMessage()));
    }

    @ExceptionHandler(AccessCodeCountException.class)
    public ResponseEntity<ErrorResponse> handleAccessCodeCount(AccessCodeCountException ex) {
        return ResponseEntity
                .status(HttpStatus.TOO_MANY_REQUESTS)
                .body(ErrorResponse.of(ErrorCode.ACCESS_CODE_LIMIT_EXCEEDED, ex.getMessage()));
    }

    @ExceptionHandler(AnalysisCountExceedException.class)
    public ResponseEntity<ErrorResponse> handleAnalysisCountExceed(AnalysisCountExceedException ex) {
        return ResponseEntity
                .status(HttpStatus.TOO_MANY_REQUESTS)
                .body(ErrorResponse.of(ErrorCode.ANALYSIS_COUNT_EXCEEDED, ex.getMessage()));
    }

    @ExceptionHandler(AgreementRequiredException.class)
    public ResponseEntity<ErrorResponse> handleAgreementRequired(AgreementRequiredException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of(ErrorCode.AGREEMENT_REQUIRED, ex.getMessage()));
    }

    @ExceptionHandler(EmailNotVerifiedException.class)
    public ResponseEntity<ErrorResponse> handleEmailNotVerified(EmailNotVerifiedException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of(ErrorCode.EMAIL_NOT_VERIFIED, ex.getMessage()));
    }

    @ExceptionHandler(InvalidSessionException.class)
    public ResponseEntity<ErrorResponse> handleInvalidSession(InvalidSessionException ex) {
        return ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(ErrorResponse.of(ErrorCode.SESSION_INVALID, ex.getMessage()));
    }

    @ExceptionHandler(SessionExpiredException.class)
    public ResponseEntity<ErrorResponse> handleSessionExpired(SessionExpiredException ex) {
        return ResponseEntity
                .status(HttpStatus.UNAUTHORIZED)
                .body(ErrorResponse.of(ErrorCode.SESSION_EXPIRED, ex.getMessage()));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ErrorResponse> handleIllegalArgument(IllegalArgumentException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of(ErrorCode.INVALID_REQUEST, ex.getMessage()));
    }
}
