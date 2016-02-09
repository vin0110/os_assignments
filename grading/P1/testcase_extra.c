#include <stdio.h>
#include "mythread.h"
#include "assert.h" 

void t1(void * who)
{
  int i;
  int re; 

  printf("t1\n");
}

int main(int argc, char *argv[])
{
  
  printf("main: pre");
  MyThreadInitExtra();
  printf("main: before");
  MyThreadCreate(t1,(void*)0);
  printf("main: after");
  MyThreadYield();
  printf("main: end");
} 


