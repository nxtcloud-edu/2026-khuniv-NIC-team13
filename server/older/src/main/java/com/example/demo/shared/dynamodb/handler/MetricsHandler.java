package com.example.demo.shared.dynamodb.handler;

import com.example.demo.config.DynamoDBProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.AttributeValue;
import software.amazon.awssdk.services.dynamodb.model.GetItemRequest;
import software.amazon.awssdk.services.dynamodb.model.GetItemResponse;
import software.amazon.awssdk.services.dynamodb.model.TransactWriteItem;
import software.amazon.awssdk.services.dynamodb.model.TransactWriteItemsRequest;
import software.amazon.awssdk.services.dynamodb.model.TransactionCanceledException;
import software.amazon.awssdk.services.dynamodb.model.UpdateItemRequest;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * metrics 집계 저장/조회 핸들러.
 *
 * NOTE: 신규 테이블을 만들지 않고, 기존 admins 테이블(Prod: pertino-prod-admin)을 재사용합니다.
 * - 실제 관리자 이메일 아이템: email = 실제 이메일
 * - metrics 아이템: email = "__METRIC_*__" (이메일 포맷과 충돌하지 않는 특수 키)
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class MetricsHandler {

    // === 키 규칙 ===
    public static final String KEY_VISITORS_TOTAL = "__METRIC_VISITORS_TOTAL__";
    public static final String KEY_ANALYSIS_TOTAL = "__METRIC_ANALYSIS_TOTAL__";

    private static final String PREFIX_DAILY_VISITORS = "__METRIC_DAILY_VISITORS_"; // + YYYY-MM-DD + "__"
    private static final String PREFIX_VISITOR_MARKER = "__METRIC_VISITOR__#"; // + YYYY-MM-DD + "#" + email

    private static final String ATTR_EMAIL = "email";
    private static final String ATTR_COUNT = "count";
    private static final String ATTR_VISITED = "visited";

    private final DynamoDbClient dynamoDbClient;
    private final DynamoDBProperties dynamoDBProperties;

    public boolean isMetricKey(String emailKey) {
        return emailKey != null && emailKey.startsWith("__METRIC_");
    }

    public void incrementVisitorsTotal() {
        incrementCounter(KEY_VISITORS_TOTAL, 1);
    }

    public void incrementAnalysisTotal() {
        incrementCounter(KEY_ANALYSIS_TOTAL, 1);
    }

    /**
     * 일일 고유 방문자(email 기준)를 기록합니다.
     * - 동일 day+email 조합은 한 번만 카운트됩니다.
     * - marker Put + dailyVisitors 카운터 증가를 트랜잭션으로 묶습니다.
     *
     * @return true면 최초 방문(해당 day에서 처음), false면 이미 카운트됨
     */
    public boolean recordDailyUniqueVisitor(LocalDate day, String email) {
        if (day == null || email == null || email.isBlank()) {
            return false;
        }

        String markerKey = buildVisitorMarkerKey(day, email);
        String dailyKey = buildDailyVisitorsKey(day);

        String tableName = dynamoDBProperties.getTables().getAdmins();

        Map<String, AttributeValue> markerItem = new HashMap<>();
        markerItem.put(ATTR_EMAIL, AttributeValue.builder().s(markerKey).build());
        markerItem.put(ATTR_VISITED, AttributeValue.builder().bool(true).build());

        Map<String, AttributeValue> dailyKeyMap = Map.of(
                ATTR_EMAIL, AttributeValue.builder().s(dailyKey).build()
        );

        Map<String, String> names = Map.of("#c", ATTR_COUNT);
        Map<String, AttributeValue> values = Map.of(":inc", AttributeValue.builder().n("1").build());

        // marker가 없을 때만 생성 -> 성공 시 dailyVisitors 카운터 증가
        TransactWriteItem putMarker = TransactWriteItem.builder()
                .put(p -> p.tableName(tableName)
                        .item(markerItem)
                        .conditionExpression("attribute_not_exists(#pk)")
                        .expressionAttributeNames(Map.of("#pk", ATTR_EMAIL)))
                .build();

        TransactWriteItem incDaily = TransactWriteItem.builder()
                .update(u -> u.tableName(tableName)
                        .key(dailyKeyMap)
                        .updateExpression("ADD #c :inc")
                        .expressionAttributeNames(names)
                        .expressionAttributeValues(values))
                .build();

        TransactWriteItemsRequest req = TransactWriteItemsRequest.builder()
                .transactItems(List.of(putMarker, incDaily))
                .build();

        try {
            dynamoDbClient.transactWriteItems(req);
            return true;
        } catch (TransactionCanceledException e) {
            // 보통 marker 조건 실패(이미 존재)인 경우가 대부분
            if (e.cancellationReasons() != null
                    && e.cancellationReasons().stream().anyMatch(r -> "ConditionalCheckFailed".equals(r.code()))) {
                return false;
            }
            log.warn("Transaction canceled while recording daily visitor: day={}, email={}, reasons={}",
                    day, email, e.cancellationReasons());
            return false;
        } catch (Exception e) {
            log.error("Error recording daily unique visitor: day={}, email={}", day, email, e);
            // 실패는 일일 카운트 증가로 처리하지 않음
            return false;
        }
    }

    public long getVisitorsTotal() {
        return getCounter(KEY_VISITORS_TOTAL);
    }

    public long getAnalysisTotal() {
        return getCounter(KEY_ANALYSIS_TOTAL);
    }

    public long getDailyVisitors(LocalDate day) {
        if (day == null) {
            return 0;
        }
        return getCounter(buildDailyVisitorsKey(day));
    }

    // === 내부 구현 ===

    private void incrementCounter(String key, long delta) {
        String tableName = dynamoDBProperties.getTables().getAdmins();

        Map<String, AttributeValue> keyMap = Map.of(
                ATTR_EMAIL, AttributeValue.builder().s(key).build()
        );

        Map<String, String> names = Map.of("#c", ATTR_COUNT);
        Map<String, AttributeValue> values = Map.of(":inc", AttributeValue.builder().n(String.valueOf(delta)).build());

        UpdateItemRequest updateItemRequest = UpdateItemRequest.builder()
                .tableName(tableName)
                .key(keyMap)
                .updateExpression("ADD #c :inc")
                .expressionAttributeNames(names)
                .expressionAttributeValues(values)
                .build();

        try {
            dynamoDbClient.updateItem(updateItemRequest);
        } catch (Exception e) {
            log.error("Error incrementing counter: key={}", key, e);
        }
    }

    private long getCounter(String key) {
        String tableName = dynamoDBProperties.getTables().getAdmins();

        Map<String, AttributeValue> keyMap = Map.of(
                ATTR_EMAIL, AttributeValue.builder().s(key).build()
        );

        GetItemRequest getItemRequest = GetItemRequest.builder()
                .tableName(tableName)
                .key(keyMap)
                .build();

        try {
            GetItemResponse response = dynamoDbClient.getItem(getItemRequest);
            if (!response.hasItem()) {
                return 0;
            }
            Map<String, AttributeValue> item = response.item();
            if (item.containsKey(ATTR_COUNT) && item.get(ATTR_COUNT).n() != null) {
                try {
                    return Long.parseLong(item.get(ATTR_COUNT).n());
                } catch (Exception ignored) {
                    return 0;
                }
            }
            return 0;
        } catch (Exception e) {
            log.error("Error getting counter: key={}", key, e);
            return 0;
        }
    }

    private String buildDailyVisitorsKey(LocalDate day) {
        return PREFIX_DAILY_VISITORS + day + "__";
    }

    private String buildVisitorMarkerKey(LocalDate day, String email) {
        return PREFIX_VISITOR_MARKER + day + "#" + email;
    }
}

