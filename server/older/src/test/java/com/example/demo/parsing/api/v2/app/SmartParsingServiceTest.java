package com.example.demo.parsing.api.v2.app;

import com.example.demo.parsing.api.v2.dto.SmartParsingResult;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SmartParsingServiceTest {

    private HttpServer httpServer;
    private AtomicReference<String> requestPath;
    private AtomicReference<String> requestBody;

    @BeforeEach
    void setUp() throws IOException {
        requestPath = new AtomicReference<>();
        requestBody = new AtomicReference<>();
        httpServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        httpServer.createContext("/", exchange -> {
            requestPath.set(exchange.getRequestURI().getPath());
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));

            byte[] responseBody = """
                    {"question_list":["q1"],"answer_list":["a1"]}
                    """.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBody.length);

            try (OutputStream outputStream = exchange.getResponseBody()) {
                outputStream.write(responseBody);
            }
        });
        httpServer.start();
    }

    @AfterEach
    void tearDown() {
        httpServer.stop(0);
    }

    @Test
    void convertUsesAnalysisServiceBaseUrlForOutboundRequest() {
        SmartParsingService smartParsingService = new SmartParsingService();
        ReflectionTestUtils.setField(
                smartParsingService,
                "analysisServiceBaseUrl",
                "http://127.0.0.1:" + httpServer.getAddress().getPort()
        );

        SmartParsingResult result = smartParsingService.convert("hello");

        assertEquals("/api/parse/convert", requestPath.get());
        assertTrue(requestBody.get().contains("\"inputData\":\"hello\""));
        assertEquals(List.of("q1"), result.questionList());
        assertEquals(List.of("a1"), result.answerList());
    }
}
