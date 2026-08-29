package com.example.demo.autocomplete.api.v2.controller;

import com.example.demo.autocomplete.api.v2.app.SetupDataService;
import com.example.demo.autocomplete.api.v2.dto.SetupListData;
import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.shared.web.v2.response.SuccessCode;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(value = "/api/setup", headers = V2ApiHeaders.MAPPING_CONDITION)
@RequiredArgsConstructor
@Tag(name = "Setup", description = "회사·직무·대학·전공 목록")
public class SetupController {

    private final SetupDataService setupDataService;

    @GetMapping("/companies")
    @Operation(summary = "회사명 목록", description = "자동완성용 회사명 문자열 배열을 반환")
    public ResponseEntity<SuccessResponse<SetupListData>> companies() {
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, new SetupListData(setupDataService.companies())));
    }

    @GetMapping("/positions")
    @Operation(summary = "직무 목록", description = "자동완성용 직무 문자열 배열을 반환")
    public ResponseEntity<SuccessResponse<SetupListData>> positions() {
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, new SetupListData(setupDataService.positions())));
    }

    @GetMapping("/universities")
    @Operation(summary = "대학명 목록", description = "자동완성용 대학명 문자열 배열을 반환")
    public ResponseEntity<SuccessResponse<SetupListData>> universities() {
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, new SetupListData(setupDataService.universities())));
    }

    @GetMapping("/majors")
    @Operation(summary = "전공 목록", description = "자동완성용 전공 문자열 배열을 반환")
    public ResponseEntity<SuccessResponse<SetupListData>> majors() {
        return ResponseEntity.ok(SuccessResponse.of(SuccessCode.SUCCESS, new SetupListData(setupDataService.majors())));
    }
}
