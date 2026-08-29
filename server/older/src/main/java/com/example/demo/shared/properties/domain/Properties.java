package com.example.demo.shared.properties.domain;

import lombok.Data;

@Data
public class Properties {

    private Long id;

    private Integer maxAccessCodePerDay;
    private Integer maxAnalysisPerDay;
}
