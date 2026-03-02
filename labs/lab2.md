# Is 2^(2n) = O(2^n)? Prove it!


No, because as the "declaration" says about the O(f(n)), we have to find a value c that is positive and get an upper bound for the 2^(2n). 
For example to have an upper bound of with f(n)*c >= 2^(2n),
our c would need to be at best 2^n, but thats not constant so it mainly depends on the size of n.

# Is 2^(n+1) = O(2^n)? Prove it!

Yes, because we can find a value c that is positive and get an upper bound for the 2^(n+1).
For example to have an upper bound of with f(n)*c >= 2^(n+1),
our c would need to be at best 2, which is constant and does not depend on the size of n.