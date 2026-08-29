package com.example.demo;

import com.example.demo.analysis.api.v2.app.AnalysisV2Service;
import com.example.demo.email.api.v2.auth.app.EmailAuthV2Service;
import com.example.demo.shared.web.v2.V2ApiHeaders;
import com.example.demo.notice.api.v2.app.NoticeV2Service;
import com.example.demo.notice.api.v2.domain.NoticeV2;
import com.example.demo.email.app.EmailEntityServicePort;
import com.example.demo.email.app.EmailService;
import com.example.demo.email.domain.Email;
import com.example.demo.email.infra.EmailRepository;
import com.example.demo.shared.properties.PertineoServiceProperties;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.data.domain.PageImpl;
import org.springframework.test.web.servlet.MockMvc;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = {
        "management.health.mail.enabled=false",
        "analysis.service.base-url=http://localhost:8080"
})
@AutoConfigureMockMvc
class V1RemovalAndV2RouteSmokeTestsTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private NoticeV2Service noticeV2Service;

    @MockitoBean
    private EmailService emailService;

    @MockitoBean
    private EmailAuthV2Service emailAuthV2Service;

    @MockitoBean
    private AnalysisV2Service analysisV2Service;

    @MockitoBean
    private EmailEntityServicePort emailEntityServicePort;

    @MockitoBean
    private EmailRepository emailRepository;

    @MockitoBean
    private JavaMailSender javaMailSender;

    @MockitoBean
    private DynamoDbClient dynamoDbClient;

    @MockitoBean
    private PertineoServiceProperties pertineoServiceProperties;

    @Test
    void removedV1EndpointsReturn404() throws Exception {
        mockMvc.perform(post("/analysis"))
                .andExpect(status().isNotFound());
        mockMvc.perform(post("/send-verify-email"))
                .andExpect(status().isNotFound());
        mockMvc.perform(post("/verify-email"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/notice"))
                .andExpect(status().isNotFound());
        mockMvc.perform(get("/notice/1"))
                .andExpect(status().isNotFound());
    }

    @Test
    void v2NoticeRouteStillRespondsWithV2Header() throws Exception {
        NoticeV2 notice = new NoticeV2();
        notice.setId(1L);
        notice.setTitle("title");
        notice.setContent("content");
        notice.setCreatedAt(LocalDateTime.of(2026, 5, 14, 0, 0));
        notice.setModifiedAt(LocalDateTime.of(2026, 5, 14, 1, 0));
        when(noticeV2Service.list(0, 10)).thenReturn(new PageImpl<>(List.of(notice)));

        mockMvc.perform(get("/api/notice")
                        .header(V2ApiHeaders.NAME, V2ApiHeaders.VALUE)
                        .param("page", "1")
                        .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.notices[0].id").value(1));
    }

    @Test
    void v2EmailCreditRouteStillRespondsWithV2Header() throws Exception {
        Email email = new Email();
        email.setEmail("student@khu.ac.kr");
        email.setCount(1);
        email.setVerificationSuccessCount(0);
        email.setValid(true);
        when(emailService.getEmailEntity(anyString())).thenReturn(email);

        mockMvc.perform(get("/api/auth/email/credit")
                        .header(V2ApiHeaders.NAME, V2ApiHeaders.VALUE)
                        .param("email", "student@khu.ac.kr"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.code").value("SUCCESS"))
                .andExpect(jsonPath("$.data.email").value("student@khu.ac.kr"));
    }

    @Test
    void v2EmailVerificationKeepsErrorWrapperWhenMemberValidationFails() throws Exception {
        when(pertineoServiceProperties.getWhiteList()).thenReturn(Collections.emptyList());

        mockMvc.perform(post("/api/auth/email/verification")
                        .header(V2ApiHeaders.NAME, V2ApiHeaders.VALUE)
                        .contentType("application/json")
                        .content("{\"email\":\"outsider@example.com\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.code").value("NOT_AUTHENTICATED"));

        verifyNoInteractions(emailService);
    }

    @Test
    void v2EmailVerificationKeepsErrorWrapperWhenThresholdValidationFails() throws Exception {
        when(pertineoServiceProperties.getWhiteList()).thenReturn(Collections.emptyList());
        Email email = new Email();
        email.setEmail("student@khu.ac.kr");
        email.setVerificationSuccessCount(11);
        when(emailRepository.findByEmail("student@khu.ac.kr")).thenReturn(email);

        mockMvc.perform(post("/api/auth/email/verification")
                        .header(V2ApiHeaders.NAME, V2ApiHeaders.VALUE)
                        .contentType("application/json")
                        .content("{\"email\":\"student@khu.ac.kr\"}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.code").value("ACCESS_CODE_LIMIT_EXCEEDED"));

        verifyNoInteractions(emailService);
    }

    @Test
    void v2AnalysisKeepsErrorWrapperWhenCreditValidationFails() throws Exception {
        when(pertineoServiceProperties.getWhiteList()).thenReturn(Collections.emptyList());
        when(pertineoServiceProperties.getAdminList()).thenReturn(Collections.emptyList());
        Email email = new Email();
        email.setEmail("student@khu.ac.kr");
        email.setCount(4);
        when(emailEntityServicePort.getEmailEntity("student@khu.ac.kr")).thenReturn(email);

        mockMvc.perform(post("/api/analysis")
                        .header(V2ApiHeaders.NAME, V2ApiHeaders.VALUE)
                        .contentType("application/json")
                        .content("{\"userId\":\"student@khu.ac.kr\"}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.code").value("ANALYSIS_COUNT_EXCEEDED"));

        verifyNoInteractions(analysisV2Service);
    }
}
