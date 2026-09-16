from pydantic import BaseModel, ConfigDict, Field, EmailStr #for emails
from datetime import datetime

class UserBase(BaseModel):
    username:str= Field(min_length=1, max_length=50)
    email:EmailStr = Field( max_length=100) #emailstr is a pydantic type that validates email addresses
    #image_file:str | None = Field(default=None, max_length=20) #optional field. can be null. default is none. max length is 20.


class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True) #configure models via config dict.

    id:int
    image_file:str | None
    image_path:str

class UserUpdate(BaseModel):
    username:str | None = Field(default=None, min_length=1, max_length=50)
    email:EmailStr | None = Field(default=None, max_length=100)
    image_file:str | None = Field(default=None, max_length=20)
    


#base class which all pydantic models inherit from
#field add constraints like min and max
#configdict configure models

class PostBase(BaseModel):
    title:str = Field(min_length=1, max_length=30)
    content:str = Field(min_length=10)

class PostCreate(PostBase):
    user_id:int 

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True) #configure models via config dict.
    #can read data from ojects with attributes (what is data with attributes???) isntead ofnjust dictionary
    #fields we want in response that are not provided by client
    id:int
    user_id:int
    date_posted:datetime
    author:UserResponse #nested model. we can access the author of a post by calling post.author. we can access the posts of a user by calling user.posts.

class PostUpdate(PostBase):
    title:str | None = Field(default=None, min_length=1, max_length=30)
    content:str | None = Field(default=None, min_length=1)
