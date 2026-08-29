package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.ConditionalCheckFailedException;
import software.amazon.awssdk.services.dynamodb.model.DeleteItemRequest;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;

import java.util.HashMap;
import java.util.Map;

/**
 * Lock 관련 DynamoDB 작업을 처리하는 핸들러
 * 분산 락 기능을 제공합니다.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class LockHandler {

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    /**
     * 분산 락 획득 시도
     * @param email 락을 획득할 이메일 키
     * @param duration 락 유지 시간(분)
     * @return 락 획득 성공 여부
     */
    public boolean tryLock(String email, int duration) {
        String lockKey = "lock:" + email;
        long ttl = System.currentTimeMillis() / 1000 + (duration * 60L);

        Map<String, AttributeValue> item = new HashMap<>();
        item.put("lock_key", AttributeValue.builder().s(lockKey).build());
        item.put("ttl", AttributeValue.builder().n(String.valueOf(ttl)).build());

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getLocks())
                .item(item)
                .conditionExpression("attribute_not_exists(lock_key)")
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            return true;
        } catch (ConditionalCheckFailedException e) {
            log.debug("Lock already exists for email: {}", email);
            return false;
        } catch (Exception e) {
            log.error("Error acquiring lock for email: {}", email, e);
            throw new RuntimeException("Failed to acquire lock", e);
        }
    }

    /**
     * 분산 락 해제
     * @param email 락을 해제할 이메일 키
     */
    public void unlock(String email) {
        String lockKey = "lock:" + email;

        Map<String, AttributeValue> key = new HashMap<>();
        key.put("lock_key", AttributeValue.builder().s(lockKey).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getLocks())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error releasing lock for email: {}", email, e);
            throw new RuntimeException("Failed to release lock", e);
        }
    }
}

