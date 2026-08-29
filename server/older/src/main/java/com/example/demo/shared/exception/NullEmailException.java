package com.example.demo.shared.exception;

public class NullEmailException extends RuntimeException{

    public NullEmailException(String msg){
        super(msg);
    }
}
