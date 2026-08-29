package com.example.demo.analysis.api.v2.dto;

import lombok.Data;

import java.util.List;

@Data
public class AnalysisV2RequestDto {

    private String userId;
    private List<String> questionList;
    private List<String> answerList;
    private String education;
    private Double gpa;
    private String major;
    private String backgroundCareerAward;
    private String linguisticAbility;
    private String certificates;
    private String company;
    private String jobPosition;
    private String jobField;
    private String division;
    private String applyUrl;
}
