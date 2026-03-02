# Lecture 1

## Sum Array


### Loop Invariant

At the start of each iteration i of the for loop, sum = A[1]+A[2]+...+A[i-1].

### Initialization: 
 
i = 1; sum = 0; 

### Maintenance

We keep on accumulating the value of each element that the array holds, onto the variable sum; Basically for each iteration we add to the sum variable the next value inside the array.

### Termination:

Once the value i exceeds n the loop terminates, that is when i= n+1. Changing the value of i to n+1 means that the loop invariant yields the **sum** of all values from the array A.

## Selection Sort 
```
SELECTION-SORT(A,n)

for i = 1 to n - 1:
    smallest = i
    for j = i + 1 to n:
        if A[j] < A[smallest]
            smallest = j
    exchange A[i] with A[smallest]
```


### Cost

| Cost | Times |
| -------- | ------- |
| c1  |  n  |
| c2  |  n - 1 |
| c3  |   ∑(i = 1 -> n - 1) t,j |
| c4  |  ∑(i = 1 -> n - 1) t,j - 1 |
| c5  |   ∑(i = 1 -> n - 1) t,j - 1  |
| c6  |  n - 2 |

T(n) = an^2 + bn + c 