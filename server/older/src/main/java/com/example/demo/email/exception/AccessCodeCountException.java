package com.example.demo.email.exception;

public class AccessCodeCountException extends RuntimeException{

    public AccessCodeCountException(String message){
        super(message);
    }
}
