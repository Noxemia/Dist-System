test_string = "GfG is best for CS and also best for Learning"
  
# initializing target word 
tar_word = "best"
  
# printing original string 
print("The original string : " + str(test_string))
  
# using rindex()
# Find last occurrence of substring
res = test_string.rindex(tar_word)
  
# print result
print("Index of last occurrence of substring is : " + str(res))