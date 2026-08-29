package com.example.demo.email.exception;

public class EmailSendFailException extends RuntimeException{

    public EmailSendFailException(String message, Throwable cause){
        super(message, cause);

    }
}
