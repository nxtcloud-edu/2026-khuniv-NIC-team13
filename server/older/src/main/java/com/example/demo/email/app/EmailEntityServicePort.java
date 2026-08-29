package com.example.demo.email.app;

import com.example.demo.email.app.util.EmailWriter;
import com.example.demo.email.domain.Email;
import com.example.demo.email.exception.EmailSendFailException;
import com.example.demo.email.infra.EmailRepository;
import com.vladsch.flexmark.ext.tables.TablesExtension;
import com.vladsch.flexmark.html.HtmlRenderer;
import com.vladsch.flexmark.parser.Parser;
import com.vladsch.flexmark.util.data.MutableDataSet;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.UnsupportedEncodingException;
import java.util.Arrays;

@Service
@RequiredArgsConstructor
@Slf4j
public class EmailEntityServicePort {

    private final EmailRepository emailRepository;
    private final JavaMailSender javaMailSender;
    private final EmailWriter emailWriter;


    public Email getEmailEntity(String email) {

        return emailRepository.findByEmail(email);
    }



    @Async
    @Transactional
    public void offerSendingMarkdownEmail(String email, String md) {
        log.info("offerSendingMarkdownEmail thread={}", Thread.currentThread().getName());

        MimeMessage message = emailWriter.createMarkdownEmail(email, md);

        try {
            long start = System.nanoTime();
            log.info("email send start");
            javaMailSender.send(message);
            long elapsedMs = (System.nanoTime() - start) / 1_000_000;
            log.info("email send done elapsedMs={}", elapsedMs);
            log.info("{\"code\" : \"{}\", \"email\" : \"{}\"}","AnalyzeEmailSendSuccess", email);
        }
        catch(Exception e){
            log.info("{\"code\" : \"{}\", \"email\" : \"{}\"}","AnalyzeEmailSendFailed", email);
            throw new EmailSendFailException(e.getMessage(), e);
        }


        Email userEmail = emailRepository.findByEmail(email);
        // 23시 59분에 분석 요청을 보내고 00시에 초기화 되면 NPE 뜸. 그래서 없을 경우 초기화하는 로직 필요해서 null 체크함
        if (userEmail == null) {
            Email emailInfo = new Email();
            emailInfo.setEmail(email);
            emailInfo.setValid(false);
            emailInfo.setCount(0);
            emailInfo.setVerificationSuccessCount(0);
            emailRepository.save(emailInfo);
        }
        else{
            userEmail.setCount(userEmail.getCount() + 1);
            emailRepository.save(userEmail);
        }

    }





}
