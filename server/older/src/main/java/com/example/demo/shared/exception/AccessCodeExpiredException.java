package com.example.demo.shared.exception;

public class AccessCodeExpiredException extends RuntimeException {

    public AccessCodeExpiredException(String msg){
        super(msg);
    }
}
