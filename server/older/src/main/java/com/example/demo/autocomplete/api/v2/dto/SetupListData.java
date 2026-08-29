package com.example.demo.autocomplete.api.v2.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
@Schema(description = "셋업(자동완성) 후보 목록")
public class SetupListData {

    @Schema(description = "후보 문자열 목록", example = "[\"삼성전자\", \"SK하이닉스\"]")
    private final List<String> list;
}
