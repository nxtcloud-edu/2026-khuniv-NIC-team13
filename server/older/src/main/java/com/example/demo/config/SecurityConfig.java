package com.example.demo.config;


import com.example.demo.shared.web.v2.V2ApiHeaders;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;

import java.util.*;

@Slf4j
@Configuration
@RequiredArgsConstructor
@EnableWebSecurity
public class SecurityConfig {

    @Value("${CORS_ALLOWED_ORIGINS:http://localhost:3000,http://localhost:8080}")
    private String corsAllowedOrigins;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .cors(corsCustomizer -> corsCustomizer.configurationSource(new CorsConfigurationSource() {

                    @Override
                    public CorsConfiguration getCorsConfiguration(HttpServletRequest request) {

                        CorsConfiguration configuration = new CorsConfiguration();

                        List<String> allowedOrigins = Arrays.asList(corsAllowedOrigins.split(","));
                        configuration.setAllowedOrigins(allowedOrigins); // 프론트엔드 도메인
                        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE","PATCH","OPTIONS"));
                        configuration.setAllowedHeaders(List.of(
                                "Authorization",
                                "Content-Type",
                                "Cookie",
                                "Set-Cookie",
                                V2ApiHeaders.NAME));
                        configuration.setAllowCredentials(true); // 인증 정보 포함 (쿠키 사용 가능)

                        return configuration;
                    }
                }));

        //csrf disable -> csrf 공격에 대한 방어...
        http.csrf(AbstractHttpConfigurer::disable);

        //Form 로그인 방식 disable
        http.formLogin((auth) -> auth.disable());
//        http.formLogin(form -> form
//                .loginPage("/admin")       // 로그인 페이지 URL
//                .loginProcessingUrl("/admin/notices") // 로그인 form action URL
//                .defaultSuccessUrl("/admin/dashboard", true)
//                .permitAll()
//        ).authorizeHttpRequests(auth -> auth
//                .requestMatchers("/admin/**","/admin").authenticated()  // 관리자 권한 필요
//                .anyRequest().permitAll()
//        );


        //HTTP Basic 인증 방식 disable
        http.httpBasic((auth) -> auth.disable());

//        http.headers(headers -> headers
//                .httpStrictTransportSecurity(hsts -> hsts.includeSubDomains(true).maxAgeInSeconds(31536000)) // HSTS 설정
//                .referrerPolicy(referrer -> referrer.policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.NO_REFERRER))
//                .frameOptions(frame -> frame.sameOrigin()) // iframe 관련 보안 설정
//                .addHeaderWriter((request, response) -> {
//                    response.setHeader("Set-Cookie", "JSESSIONID=" + request.getSession().getId() + "; Path=/; HttpOnly; Secure; SameSite=None");
//                })
//        );

        //경로별 인가 작업
//        http.authorizeHttpRequests((auth) -> auth
//                .requestMatchers("/status","/my-info","/stream/analysis/**","/notice","/notice/**", "/oauth2/failure","/oauth2/authorization/google").permitAll()
//                .anyRequest().authenticated());


        //세션 설정 : STATELESS
        http.sessionManagement((session) -> session
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS));

        return http.build();
    }



}