package com.example.demo.parsing.api.v2.controller;

import com.example.demo.parsing.api.v2.app.SmartParsingService;
import com.example.demo.parsing.api.v2.dto.SmartParsingResult;
import com.example.demo.shared.web.v2.response.SuccessResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class SmartParsingControllerTest {

    @Test
    void parseResumeDelegatesToServiceAndKeepsSuccessResponseShape() {
        SmartParsingService smartParsingService = mock(SmartParsingService.class);
        SmartParsingResult parsingResult = new SmartParsingResult(List.of("q1"), List.of("a1"));
        when(smartParsingService.convert("raw input")).thenReturn(parsingResult);
        SmartParsingController controller = new SmartParsingController(smartParsingService);

        ResponseEntity<SuccessResponse<SmartParsingResult>> response = controller.parseResume("raw input");

        assertEquals(200, response.getStatusCode().value());
        assertNotNull(response.getBody());
        assertTrue(response.getBody().isSuccess());
        assertEquals("SUCCESS", response.getBody().getCode());
        assertEquals("스마트 파싱 성공", response.getBody().getMessage());
        assertEquals(parsingResult, response.getBody().getData());
        verify(smartParsingService).convert("raw input");
    }
}
