package com.example.demo.parsing.api.v2.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record SmartParsingResult(
        @JsonProperty("question_list") List<String> questionList,
        @JsonProperty("answer_list") List<String> answerList
) {
}
