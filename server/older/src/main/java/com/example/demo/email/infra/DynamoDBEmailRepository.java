package com.example.demo.email.infra;

import com.example.demo.config.DynamoDBProperties;
import com.example.demo.email.domain.Email;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Repository;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.DeleteItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.PutItemRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanRequest;
import software.amazon.awssdk.services.dynamodb.model.ScanResponse;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Email 엔티티용 DynamoDB Repository 구현
 */
@Repository
@RequiredArgsConstructor
@Slf4j
public class DynamoDBEmailRepository implements EmailRepository {
    
    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    @Override
    public Email findByEmail(String email) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getEmails())
                .key(key)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            
            if (!response.hasItem()) {
                return null;
            }

            return mapToEmail(response.item());
        } catch (Exception e) {
            log.error("Error finding email: {}", email, e);
            return null;
        }
    }

    @Override
    public Email save(Email email) {
        Map<String, AttributeValue> item = new HashMap<>();
        item.put("email", AttributeValue.builder().s(email.getEmail()).build());
        
        if (email.getCount() != null) {
            item.put("count", AttributeValue.builder().n(String.valueOf(email.getCount())).build());
        } else {
            item.put("count", AttributeValue.builder().n("0").build());
        }
        
        if (email.getVerificationSuccessCount() != null) {
            item.put("verificationSuccessCount", AttributeValue.builder().n(String.valueOf(email.getVerificationSuccessCount())).build());
        } else {
            item.put("verificationSuccessCount", AttributeValue.builder().n("0").build());
        }
        
        if (email.getValid() != null) {
            item.put("valid", AttributeValue.builder().bool(email.getValid()).build());
        } else {
            item.put("valid", AttributeValue.builder().bool(false).build());
        }

        PutItemRequest putItemRequest = PutItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getEmails())
                .item(item)
                .build();

        try {
            dynamoDbClient.putItem(putItemRequest);
            return email;
        } catch (Exception e) {
            log.error("Error saving email", e);
            throw new RuntimeException("Failed to save email", e);
        }
    }

    @Override
    public void deleteAll() {
        List<Email> emails = findAll();
        for (Email email : emails) {
            deleteEmail(email.getEmail());
        }
    }

    @Override
    public List<Email> findAll() {
        List<Email> emails = new ArrayList<>();
        Map<String, AttributeValue> lastEvaluatedKey = null;

        try {
            do {
                ScanRequest.Builder scanRequestBuilder = ScanRequest.builder()
                        .tableName(dynamoDBProperties.getTables().getEmails());

                if (lastEvaluatedKey != null) {
                    scanRequestBuilder.exclusiveStartKey(lastEvaluatedKey);
                }

                ScanResponse response = dynamoDbClient.scan(scanRequestBuilder.build());
                
                for (Map<String, AttributeValue> item : response.items()) {
                    emails.add(mapToEmail(item));
                }

                lastEvaluatedKey = response.lastEvaluatedKey();
            } while (lastEvaluatedKey != null && !lastEvaluatedKey.isEmpty());

            return emails;
        } catch (Exception e) {
            log.error("Error finding all emails", e);
            throw new RuntimeException("Failed to find all emails", e);
        }
    }

    // === Private helper methods ===

    private void deleteEmail(String email) {
        Map<String, AttributeValue> key = new HashMap<>();
        key.put("email", AttributeValue.builder().s(email).build());

        DeleteItemRequest deleteItemRequest = DeleteItemRequest.builder()
                .tableName(dynamoDBProperties.getTables().getEmails())
                .key(key)
                .build();

        try {
            dynamoDbClient.deleteItem(deleteItemRequest);
        } catch (Exception e) {
            log.error("Error deleting email: {}", email, e);
            throw new RuntimeException("Failed to delete email", e);
        }
    }

    private Email mapToEmail(Map<String, AttributeValue> item) {
        Email email = new Email();
        
        if (item.containsKey("email")) {
            email.setEmail(item.get("email").s());
        }
        if (item.containsKey("count")) {
            try {
                email.setCount(Integer.parseInt(item.get("count").n()));
            } catch (Exception e) {
                email.setCount(0);
            }
        }
        if (item.containsKey("verificationSuccessCount")) {
            try {
                email.setVerificationSuccessCount(Integer.parseInt(item.get("verificationSuccessCount").n()));
            } catch (Exception e) {
                email.setVerificationSuccessCount(0);
            }
        }
        if (item.containsKey("valid")) {
            email.setValid(item.get("valid").bool());
        }
        
        return email;
    }
}
