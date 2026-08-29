package com.example.demo.email.app.util;

import com.example.demo.email.exception.EmailSendFailException;
import com.example.demo.shared.dynamodb.handler.AccessCodeHandler;
import com.vladsch.flexmark.ext.tables.TablesExtension;
import com.vladsch.flexmark.html.HtmlRenderer;
import com.vladsch.flexmark.parser.Parser;
import com.vladsch.flexmark.util.data.MutableDataSet;
import jakarta.mail.Message;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import lombok.RequiredArgsConstructor;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

import java.io.UnsupportedEncodingException;
import java.util.Arrays;

@Component
@RequiredArgsConstructor
public class EmailWriter {

    private final JavaMailSender javaMailSender;
    private final AccessCodeHandler accessCodeHandler;

    public MimeMessage createMarkdownEmail(String email, String md){

        MutableDataSet options = new MutableDataSet();
        options.set(Parser.EXTENSIONS, Arrays.asList(TablesExtension.create()));


        Parser parser = Parser.builder(options).build();
        HtmlRenderer renderer = HtmlRenderer.builder(options).build();
        String htmlContent = renderer.render(parser.parse(md));
        MimeMessage message = javaMailSender.createMimeMessage();

        try {
            message.setFrom(new InternetAddress("no-reply@pertineo.vercel.app", "Pertineo"));
            message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(email));
            message.setSubject("Pertineo 자기소개서 분석 보고서");
            message.setContent(convertToEmailTemplate(htmlContent), "text/html; charset=UTF-8");


        }
        catch (MessagingException | UnsupportedEncodingException e) {
            throw new EmailSendFailException("이메일 전송에 실패했습니다", e);
        }

        return message;
    }

    public MimeMessage CreateMail(String email) {
        int accessCode = accessCodeHandler.createAccessCode(email, 10);

        MimeMessage message = javaMailSender.createMimeMessage();

        try {
            String body = """
                    <h2>[Pertineo] 이메일 인증번호 안내</h2>
                             <p>Pertineo를 이용해 주셔서 감사합니다.<br />
                             아래 인증번호를 입력하여 이메일 인증을 완료해 주세요.</p>
                       
                             <div class="code-box" id="code">"""+  accessCode + """ 
                             </div>
                       
                             <p>인증번호는 본 메일 발송 시점부터 <strong>10분간 유효</strong>합니다.</p>
                    """;
            message.setFrom(new InternetAddress("no-reply@pertineo.vercel.app", "Pertineo"));
            message.setRecipients(Message.RecipientType.TO, InternetAddress.parse(email));
            message.setSubject("Pertineo 이메일 인증 코드");
            message.setContent(convertToEmailTemplate(body), "text/html; charset=UTF-8");


        } catch (MessagingException | UnsupportedEncodingException e) {
            throw new EmailSendFailException("이메일 전송에 실패했습니다", e);
        }

        return message;
    }

    private String convertToEmailTemplate(String content) {
        return """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8" />
            <title>Pertineo 이메일 서비스</title>
            <style>
                body {
                    font-family: 'Arial', sans-serif;
                    background-color: #f9f9f9;
                    margin: 0;
                    padding: 0;
                }
                .wrapper {
                    width: 60%;
                    max-width: 900px;
                    min-width: 300px;
                    margin: 10px auto 0;
                    padding: 0 16px;
                }
                        
            
                @media (max-width: 768px) {
                    .wrapper {
                        width: 90%;
                        padding: 0 12px;
                    }
                }
                .header {
                    background-color: #990D17;
                    color: #ffffff;
                    padding: 16px 0;
                    text-align: center;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 8px 8px 0 0;
                }
                .container {
                    background: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-top: none;
                    border-radius: 0 0 8px 8px;
                    padding: 30px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.04);
                }
                h2 {
                    color: #222;
                    font-size: 20px;
                    margin-bottom: 16px;
                }
                p {
                    font-size: 14px;
                    line-height: 1.6;
                    margin: 0 0 10px;
                }
                .code-box {
                    margin: 20px 0;
                    padding: 15px;
                    background: #f1f3f5;
                    border-radius: 8px;
                    font-size: 20px;
                    font-weight: bold;
                    text-align: center;
                    letter-spacing: 2px;
                    cursor: pointer;
                    user-select: all;
                }
                .footer {
                    font-size: 12px;
                    color: #999;
                    margin-top: 20px;
                    text-align: center;
                }
            </style>
        </head>
        <body style="margin: 0; padding: 0; background-color: #f0f0f0;">
            <div class="wrapper">
                <div class="header">Pertineo</div>
                <div class="container">
                    """ + content + """
                    <div class="footer">© Pertineo. All rights reserved by Pertineo & Kyung Hee University.</div>
                </div>
            </div>
        </body>
        </html>
    """;
    }
}
