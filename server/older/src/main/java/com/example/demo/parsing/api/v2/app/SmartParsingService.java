package com.example.demo.parsing.api.v2.app;

import com.example.demo.parsing.api.v2.dto.SmartParsingResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

@Service
public class SmartParsingService {

    private static final String PARSE_CONVERT_PATH = "/api/parse/convert";

    private final WebClient webClient = WebClient.create();

    @Value("${analysis.service.base-url}")
    private String analysisServiceBaseUrl;

    public SmartParsingResult convert(String inputData) {
        return webClient.post()
                .uri(analysisServiceBaseUrl + PARSE_CONVERT_PATH)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of("inputData", inputData))
                .retrieve()
                .bodyToMono(SmartParsingResult.class)
                .block();
    }
}
