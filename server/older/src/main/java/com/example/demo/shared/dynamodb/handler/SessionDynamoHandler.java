package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import com.example.demo.config.PertineoSessionProperties;
import lombok.RequiredArgsConstructor;
import lombok.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;
import software.amazon.awssdk.services.dynamodb.model.QueryRequest;
import software.amazon.awssdk.services.dynamodb.model.QueryResponse;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Component
@RequiredArgsConstructor
@Slf4j
public class SessionDynamoHandler {

    private static final String EMAIL_INDEX_NAME = "email-index";

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;
    private final PertineoSessionProperties sessionProperties;

    /**
     * 이메일당 활성 세션이 있으면 TTL만 갱신하고, 없으면 새 세션을 만듭니다.
     */
    public UpsertActiveSessionResult upsertActiveSessionForEmail(String email) {
        Instant now = Instant.now();
        int ttlMinutes = sessionProperties.getTtlMinutes();
        long ttl = now.getEpochSecond() + (ttlMinutes * 60L);

        Optional<SessionRecord> existing = findActiveSessionForEmail(email, now);
        if (existing.isPresent()) {
            SessionRecord e = existing.get();
            SessionRecord session = writeSession(e.getSessionId(), e.getEmail(), e.getStatus(), ttl);
            return new UpsertActiveSessionResult(session, true);
        }

        String sessionId = "sess_" + UUID.randomUUID();
        SessionRecord session = writeSession(sessionId, email, "ACTIVE", ttl);
        return new UpsertActiveSessionResult(session, false);
    }

    private SessionRecord writeSession(String sessionId, String email, String status, long ttl) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("session_id", AttributeValue.builder().s(sessionId).build());
        item.put("email", AttributeValue.builder().s(email).build());
        item.put("status", AttributeValue.builder().s(status).build());
        item.put("ttl", AttributeValue.builder().n(String.valueOf(ttl)).build());

        PutItemRequest request = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getSessions())
                .item(item)
                .build();

        dynamoDbClient.putItem(request);
        return new SessionRecord(sessionId, email, status, ttl);
    }

    /**
     * 이메일 GSI로 조회합니다. 운영 테이블에 동일 이름의 GSI가 있어야 합니다.
     */
    public Optional<SessionRecord> findActiveSessionForEmail(String email, Instant now) {
        Map<String, AttributeValue> exprValues = new HashMap<>();
        exprValues.put(":email", AttributeValue.builder().s(email).build());

        QueryRequest request = QueryRequest.builder()
                .tableName(dynamoDBProperties.getTables().getSessions())
                .indexName(EMAIL_INDEX_NAME)
                .keyConditionExpression("email = :email")
                .expressionAttributeValues(exprValues)
                .build();

        QueryResponse response = dynamoDbClient.query(request);
        for (Map<String, AttributeValue> item : response.items()) {
            SessionRecord record = mapToRecord(item);
            if ("ACTIVE".equals(record.status) && !record.isExpired(now)) {
                return Optional.of(record);
            }
        }
        return Optional.empty();
    }

    public Optional<SessionRecord> get(String sessionId) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("session_id", AttributeValue.builder().s(sessionId).build());

        GetItemRequest request = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getSessions())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(request);
            if (!response.hasItem()) {
                return Optional.empty();
            }

            Map<String, AttributeValue> item = response.item();
            return Optional.of(mapToRecord(item));
        } catch (Exception e) {
            log.error("Error getting session sessionId={}", sessionId, e);
            return Optional.empty();
        }
    }

    public Optional<SessionRecord> extend(String sessionId, int extendMinutes) {
        return get(sessionId).map(existing -> {
            long newTtl = existing.ttl + (extendMinutes * 60L);
            return writeSession(existing.sessionId, existing.email, existing.status, newTtl);
        });
    }

    /**
     * 세션 만료(ttl)를 '현재 시각 기준 fixedMinutes 후'로 재설정합니다.
     */
    public Optional<SessionRecord> extendFixedFromNow(String sessionId, int fixedMinutes, Instant now) {
        return get(sessionId).map(existing -> {
            long newTtl = now.getEpochSecond() + (fixedMinutes * 60L);
            return writeSession(existing.sessionId, existing.email, existing.status, newTtl);
        });
    }

    private static SessionRecord mapToRecord(Map<String, AttributeValue> item) {
        String sessionId = item.get("session_id").s();
        String email = item.get("email").s();
        String status = item.containsKey("status") ? item.get("status").s() : "ACTIVE";
        long ttl = item.containsKey("ttl") ? Long.parseLong(item.get("ttl").n()) : 0L;
        return new SessionRecord(sessionId, email, status, ttl);
    }

    @Value
    public static class SessionRecord {
        String sessionId;
        String email;
        String status;
        long ttl;

        public Instant expiresAt() {
            return Instant.ofEpochSecond(ttl);
        }

        public boolean isExpired(Instant now) {
            return ttl > 0 && ttl < now.getEpochSecond();
        }
    }

    public record UpsertActiveSessionResult(SessionRecord session, boolean refreshedExisting) {
    }
}

