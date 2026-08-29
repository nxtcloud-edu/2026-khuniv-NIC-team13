package com.example.demo.config;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;
import java.util.List;

/**
 * Caffeine 캐시 설정
 * Redis를 대체하여 로컬 캐시를 사용합니다.
 */
@Configuration
public class CacheConfig {

    /**
     * 일일 사용량 제한 캐시
     * Key: email:limit_type (예: "user@example.com:accessCode")
     * Value: count (Integer)
     * TTL: 24시간
     */
    @Bean
    public Cache<String, Integer> dailyLimitCache() {
        return Caffeine.newBuilder()
                .expireAfterWrite(Duration.ofHours(24))
                .maximumSize(1000)
                .recordStats()
                .build();
    }

    /**
     * 설정 데이터 캐시
     * Key: config_type (예: "admins", "whitelist")
     * Value: List<String> 또는 Object
     * TTL: 30분
     */
    @Bean
    public Cache<String, List<String>> configListCache() {
        return Caffeine.newBuilder()
                .expireAfterWrite(Duration.ofMinutes(30))
                .maximumSize(100)
                .recordStats()
                .build();
    }

    /**
     * Properties 설정 캐시
     * Key: "properties"
     * Value: Properties 객체
     * TTL: 30분
     */
    @Bean
    public Cache<String, Object> propertiesCache() {
        return Caffeine.newBuilder()
                .expireAfterWrite(Duration.ofMinutes(30))
                .maximumSize(10)
                .recordStats()
                .build();
    }
}

