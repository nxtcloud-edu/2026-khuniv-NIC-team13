package com.example.demo.analysis.api.v2.controller;

import com.example.demo.analysis.app.CreditGuard;
import com.example.demo.analysis.api.v2.app.AnalysisV2Service;
import com.example.demo.analysis.api.v2.dto.AnalysisV2RequestDto;
import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.shared.security.MemberGuard;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;


@RestController
@RequestMapping(value = "/api/analysis", headers = V2ApiHeaders.MAPPING_CONDITION)
@RequiredArgsConstructor
@Tag(name = "Analysis V2", description = "자기소개서 분석 (v2)")
public class AnalysisV2Controller {
    private final AnalysisV2Service analysisV2Service;
    private final MemberGuard memberGuard;
    private final CreditGuard creditGuard;

    @PostMapping("")
    @Operation(summary = "자기소개서 분석", description = "자기소개서 분석 스트림을 제공합니다.")
    public SseEmitter analysis(@RequestBody AnalysisV2RequestDto analysisV2RequestDto){
        memberGuard.requireMember(analysisV2RequestDto.getUserId());
        creditGuard.requireCredit(analysisV2RequestDto.getUserId());
        return analysisV2Service.connect(analysisV2RequestDto);
    }

}
