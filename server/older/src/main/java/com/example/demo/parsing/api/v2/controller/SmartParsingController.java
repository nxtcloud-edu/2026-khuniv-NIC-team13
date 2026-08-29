package com.example.demo.parsing.api.v2.controller;

import com.example.demo.parsing.api.v2.app.SmartParsingService;
import com.example.demo.parsing.api.v2.dto.SmartParsingResult;
import com.example.demo.shared.web.v2.response.SuccessCode;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/parse")
@RequiredArgsConstructor
@Tag(name = "Parse Input V2", description = "입력 스마트 파싱 (v2)")
public class SmartParsingController {

    private final SmartParsingService smartParsingService;

    @PostMapping("/convert")
    @Operation(summary = "입력 파싱", description = "입력 파싱")
    public ResponseEntity<SuccessResponse<SmartParsingResult>> parseResume(@RequestBody String inputData) {
        SmartParsingResult response = smartParsingService.convert(inputData);
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, "스마트 파싱 성공", response));
    }
}
