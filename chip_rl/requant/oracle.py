"""Integer oracle uses signed floor division; RTL rounds unsigned magnitudes."""
def lane(a,scale,shift,zp):
 if not (-2**31<=a<2**31 and 0<=scale<2**16 and 0<=shift<=47 and -128<=zp<=127):raise ValueError('input domain')
 q,r=divmod(a*scale,1<<shift)
 if 2*r>(1<<shift) or (2*r==(1<<shift) and q%2):q+=1
 return max(-128,min(127,q+zp))
def expected(row,n):
 return sum((lane(row['acc'][i],row['scale'],row['shift'],row['zp'])&255)<<(8*i) for i in range(n) if row['mask']>>i&1)
def check(row,n,value):
 if type(value) is not int or not 0<=value<2**32 or value!=expected(row,n):raise ValueError('exact requantization mismatch')
