package com.example.demo.shared.cache;

import com.example.demo.shared.dynamodb.handler.AdminHandler;
import com.example.demo.shared.dynamodb.handler.PropertiesHandler;
import com.example.demo.shared.dynamodb.handler.WhiteListHandler;
import com.example.demo.shared.properties.domain.Properties;
import com.github.benmanes.caffeine.cache.Cache;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * 로컬 캐시 서비스
 * Caffeine 캐시를 사용하여 일일 사용량 제한 및 설정 데이터를 관리합니다.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class LocalCacheService {

    private final Cache<String, Integer> dailyLimitCache;
    private final Cache<String, List<String>> configListCache;
    private final Cache<String, Object> propertiesCache;
    
    private final AdminHandler adminHandler;
    private final WhiteListHandler whiteListHandler;
    private final PropertiesHandler propertiesHandler;

    // === 일일 사용량 제한 관련 ===
    
    /**
     * 일일 사용량 조회
     * @param email 이메일 주소
     * @param limitType 제한 타입 (accessCode, analysis 등)
     * @return 현재 사용량
     */
    public int getDailyCount(String email, String limitType) {
        String key = buildDailyLimitKey(email, limitType);
        Integer count = dailyLimitCache.getIfPresent(key);
        return count != null ? count : 0;
    }

    /**
     * 일일 사용량 증가
     * @param email 이메일 주소
     * @param limitType 제한 타입
     * @return 증가 후 사용량
     */
    public int incrementDailyCount(String email, String limitType) {
        String key = buildDailyLimitKey(email, limitType);
        Integer currentCount = dailyLimitCache.getIfPresent(key);
        int newCount = (currentCount != null ? currentCount : 0) + 1;
        dailyLimitCache.put(key, newCount);
        log.debug("Daily count incremented: key={}, count={}", key, newCount);
        return newCount;
    }

    /**
     * 일일 사용량 설정
     * @param email 이메일 주소
     * @param limitType 제한 타입
     * @param count 설정할 값
     */
    public void setDailyCount(String email, String limitType, int count) {
        String key = buildDailyLimitKey(email, limitType);
        dailyLimitCache.put(key, count);
    }

    /**
     * 일일 사용량 초기화 (특정 이메일)
     */
    public void resetDailyCount(String email, String limitType) {
        String key = buildDailyLimitKey(email, limitType);
        dailyLimitCache.invalidate(key);
    }

    /**
     * 모든 일일 사용량 캐시 초기화
     */
    public void resetAllDailyLimits() {
        dailyLimitCache.invalidateAll();
        log.info("All daily limit caches invalidated");
    }

    private String buildDailyLimitKey(String email, String limitType) {
        return email + ":" + limitType;
    }

    // === 설정 캐시 관련 ===

    /**
     * 관리자 목록 조회 (캐시 우선)
     */
    public List<String> getAdminList() {
        return configListCache.get("admins", key -> {
            log.debug("Loading admin list from DynamoDB");
            try {
                return adminHandler.findAllAdminEmails();
            } catch (Exception e) {
                log.warn("Failed to load admin list: {}", e.getMessage());
                return new ArrayList<>();
            }
        });
    }

    /**
     * 화이트리스트 조회 (캐시 우선)
     */
    public List<String> getWhiteList() {
        return configListCache.get("whitelist", key -> {
            log.debug("Loading whitelist from DynamoDB");
            try {
                return whiteListHandler.findAllWhiteListEmails();
            } catch (Exception e) {
                log.warn("Failed to load whitelist: {}", e.getMessage());
                return new ArrayList<>();
            }
        });
    }

    /**
     * 시스템 설정 조회 (캐시 우선)
     */
    public Optional<Properties> getProperties() {
        Object cached = propertiesCache.get("properties", key -> {
            log.debug("Loading properties from DynamoDB");
            try {
                return propertiesHandler.findProperties().orElse(null);
            } catch (Exception e) {
                log.warn("Failed to load properties: {}", e.getMessage());
                return null;
            }
        });
        return Optional.ofNullable((Properties) cached);
    }

    /**
     * 설정 캐시 갱신 (수동)
     */
    public void refreshConfigCache() {
        configListCache.invalidateAll();
        propertiesCache.invalidateAll();
        log.info("Config caches refreshed");
    }

    /**
     * 관리자 목록 캐시만 갱신
     */
    public void refreshAdminCache() {
        configListCache.invalidate("admins");
    }

    /**
     * 화이트리스트 캐시만 갱신
     */
    public void refreshWhiteListCache() {
        configListCache.invalidate("whitelist");
    }

    /**
     * 시스템 설정 캐시만 갱신
     */
    public void refreshPropertiesCache() {
        propertiesCache.invalidate("properties");
    }

    // === 캐시 통계 ===

    /**
     * 일일 제한 캐시 통계 조회
     */
    public String getDailyLimitCacheStats() {
        return dailyLimitCache.stats().toString();
    }

    /**
     * 설정 캐시 통계 조회
     */
    public String getConfigCacheStats() {
        return configListCache.stats().toString();
    }
}
