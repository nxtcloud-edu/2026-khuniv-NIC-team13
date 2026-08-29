package com.example.demo.email.app;

import com.example.demo.shared.exception.EmailNotVerifiedException;
import com.example.demo.email.app.util.EmailWriter;
import com.example.demo.email.domain.Email;
import com.example.demo.email.exception.EmailSendFailException;
import com.example.demo.email.infra.EmailRepository;
// import com.example.demo.shared.redis.RedisHandler; // Redis는 DynamoDB로 마이그레이션 완료
import com.vladsch.flexmark.ext.tables.TablesExtension;
import com.vladsch.flexmark.util.data.MutableDataSet;
import com.vladsch.flexmark.html.HtmlRenderer;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;

import lombok.RequiredArgsConstructor;
// import org.springframework.data.redis.core.RedisTemplate; // Redis는 DynamoDB로 마이그레이션 완료
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Async;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import com.vladsch.flexmark.parser.Parser;
import org.springframework.transaction.annotation.Transactional;

import java.io.UnsupportedEncodingException;
import java.time.Duration;
import java.util.Arrays;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class EmailService {

    private final EmailRepository emailRepository;
    private final JavaMailSender javaMailSender;
    private final EmailWriter emailWriter;


    @Async
    @Transactional
    public void sendVerificationEmail(String email) {
        MimeMessage message = emailWriter.CreateMail(email);
        Email userEmail = emailRepository.findByEmail(email);
        if (userEmail == null) {
            Email emailInfo = new Email();
            emailInfo.setEmail(email);
            emailInfo.setValid(false);
            emailInfo.setCount(0);
            emailInfo.setVerificationSuccessCount(0);
            emailRepository.save(emailInfo);
            userEmail = emailInfo;
        }

        try {
            javaMailSender.send(message);
        } catch (Exception e) {
            throw new EmailSendFailException("이메일 전송에 실패했습니다: " + e.getMessage(), e);
        }
        finally {
            userEmail.setVerificationSuccessCount(userEmail.getVerificationSuccessCount() + 1);
            emailRepository.save(userEmail);
        }

    }

    @Transactional(readOnly = true)
    public void requireEmailVerified(String email) {
        Email userEmail = emailRepository.findByEmail(email);
        if (userEmail == null || !Boolean.TRUE.equals(userEmail.getValid())) {
            throw new EmailNotVerifiedException("이메일 인증을 먼저 완료해 주세요.");
        }
    }

    @Transactional
    public Email getEmailEntity(String email) {
        Email userEmail = emailRepository.findByEmail(email);
        if (userEmail == null) {
            Email emailInfo = new Email();
            emailInfo.setEmail(email);
            emailInfo.setValid(true);
            emailInfo.setCount(0);
            emailInfo.setVerificationSuccessCount(0);
            emailRepository.save(emailInfo);
            return emailInfo;
        }
        else{
            userEmail.setValid(true);
            emailRepository.save(userEmail);
            return userEmail;
        }

    }

    @Scheduled(cron = "0 0 0 * * *", zone = "Asia/Seoul")
    public void resetCount() {
        emailRepository.deleteAll();
    }


}
