from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
#from fastapi.responses import HTMLResponse #allows a html fornend for endport
from fastapi.staticfiles import StaticFiles  #allows us to serve static files like css, js, images etc
#jinja2 alr with 'fastapi[standard]'
from fastapi.templating import Jinja2Templates

from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
     http_exception_handler,
     request_validation_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException 

from fastapi import HTTPException,status, Depends # depends add dependancy injection. how to inject db session into our routes

from schemas import PostCreate, PostResponse, UserCreate, UserResponse, PostUpdate, UserUpdate

from typing import Annotated


from sqlalchemy import select # style for querying 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models
from database import Base, engine, get_db #base and engine for creating tables and connecting to db. get_db is a function that returns a db session

@asynccontextmanager
async def lifespan(app: FastAPI):
     async with engine.begin() as connection:
          await connection.run_sync(Base.metadata.create_all)
     yield
     await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"),name="static") #mount the static files directory to the /static endpoint

app.mount("/media", StaticFiles(directory="media"), name="media") #mount the media files directory to the /media endpoint

templates=Jinja2Templates(directory="templates", ) #directory where the html files are stored


#@app.get("/", response_class=HTMLResponse, include_in_schema=False) #include_in_schema=False will hide the route from the docs
#@app.get("/posts", response_class=HTMLResponse) #can stack routes if we want to show both pages same ocntent

@app.get("/", include_in_schema=False, name="home") #include_in_schema=False  =will hide the route from the docs
@app.get("/posts", include_in_schema=False, name='Posts') #can stack routes if we want to show both pages same ocntent
async def home(request:Request, db:Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()

    return templates.TemplateResponse(
         request,
         "home.html",
         {"posts":posts, "title":"Home"}
    )
#     return templates.TemplateResponse(request,
#                                     "home.html",
#                                     {'posts':posts, 'title': 'Home Page'},
#                                     ) #pass the request object to the template, and the name of the template, and a dictionary of variables to pass to the template


@app.get("/posts/{post_id}", include_in_schema=False, name="post_page") #not in doc since this is returning html
async def post_page(request:Request, post_id:int, db:Annotated[AsyncSession,Depends(get_db)]):
     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
     post = result.scalars().first()

     if post:
          title=post.title[:50]
          return templates.TemplateResponse(
               request,
               "post.html",
               {"post":post, "title":title}
          )

     raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="post not found",
     )

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
     request: Request,
     user_id: int,
     db: Annotated[AsyncSession, Depends(get_db)]
):
     result = await db.execute(select(models.User).where(models.User.id==user_id))
     user = result.scalars().first()

     if not user:
          raise HTTPException(
               status_code= status.HTTP_404_NOT_FOUND,
               detail = "user not found"
          )

     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id==user_id))
     posts= result.scalars().all()

     return templates.TemplateResponse(
          request,
          "user_posts.html",
          {"posts":posts, "user": user, "title": f"{user.username}'s Posts"}
     )

@app.post(
          "/api/users",
          response_model=UserResponse,
          status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserCreate, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(
          select(models.User).where(models.User.username == user.username)
     )

     existing_user = result.scalars().first()

     if existing_user:
          raise HTTPException(
               status_code= status.HTTP_400_BAD_REQUEST,
               detail="username already exists",
          )

     #same for email
     
     result = await db.execute(
          select(models.User).where(models.User.email == user.email)
     )

     existing_email = result.scalars().first()

     if existing_email:
          raise HTTPException(
               status_code= status.HTTP_400_BAD_REQUEST,
               detail="email already in use",
          )

     new_user = models.User(
          username=user.username,
          email= user.email,
     )

     db.add(new_user) #stages insert
     await db.commit() #executes it
     await db.refresh(new_user) #reloads object from database

     return new_user 

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int,  db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(
               select(models.User).where(models.User.id == user_id)
          )

     user = result.scalars().first()

     if user:
          return user

     raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="user not found",
     )

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int,  db:Annotated[AsyncSession, Depends(get_db)]):
     result=await db.execute(select(models.User).where(models.User.id==user_id))
     user=result.scalars().first()

     if not user:
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="user not found",
          )

     result= await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.user_id == user_id))
     posts = result.scalars().all()
     return posts

@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id:int, user_update:UserUpdate, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.User).where(models.User.id==user_id))
     user = result.scalars().first()

     if not user:
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="user not found",
          )

     if user_update.username is not None and user_update.username != user.username: # checking if new username not same as old username. if not, check if new username already exists in db. if it does, raise 400
          result = await db.execute(select(models.User).where(models.User.username==user_update.username))
          existing_user = result.scalars().first()

          if existing_user:
               raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="username already exists",
               )

     if user_update.email is not None and user_update.email != user.email: # checking if new email not same as old email. if not, check if new email already exists in db. if it does, raise 400
          result = await db.execute(select(models.User).where(models.User.email==user_update.email))
          existing_email = result.scalars().first()

          if existing_email:
               raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="email already in use",
               )

     if user_update.username is not None:
          user.username = user_update.username

     if user_update.email is not None:
          user.email = user_update.email

     if user_update.image_file is not None:
          user.image_file = user_update.image_file

     await db.commit()
     await db.refresh(user)
     return user


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id:int, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.User).where(models.User.id==user_id))
     user = result.scalars().first()

     if not user:
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="user not found",
          )

     await db.delete(user)
     await db.commit()

@app.get("/api/posts", response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
     posts = result.scalars().all()
     return posts

@app.post(
          "/api/posts",
          response_model=PostResponse,
          status_code=status.HTTP_201_CREATED
)
async def create_post(post:PostCreate, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.User).where(models.User.id==post.user_id))
     user = result.scalars().first()

     if not user:
          raise HTTPException(
               status_code= status.HTTP_404_NOT_FOUND,
               detail="user not found",
          )

     new_post = models.Post(
          title=post.title,
          content=post.content,
          user_id=post.user_id,
     )

     db.add(new_post)
     await db.commit()
     await db.refresh(new_post, ["author"])
     return new_post


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
     post = result.scalars().first()

     if not post:
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="post not found"
          )
     return post


@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_full(post_id: int, post_data: PostCreate, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
     post = result.scalars().first()

     if not post: #raise 404 if post doesnt exist 
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="post not found"
          )
     if post_data.user_id != post.user_id: #check if user_id in request body is same as user_id of post. if not, raise 403

          result=await db.execute(select(models.User).where(models.User.id==post_data.user_id))
          user=result.scalars().first()

          if not user:
               raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user not found"
               )
     post.title=post_data.title
     post.content=post_data.content
     post.user_id=post_data.user_id
     await db.commit()
     await db.refresh(post, ["author"])
     return post

@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id==post_id))
     post = result.scalars().first()

     if not post: #raise 404 if post doesnt exist 
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="post not found"
          )

     update_data = post_data.dict(exclude_unset=True) #exclude_unset=True will exclude fields that are not set in the request body

     for field,value in update_data.items():
          setattr(post, field, value) #setattr(object, attribute, value) sets the attribute of the object to the value
 
     await db.commit()
     await db.refresh(post, ["author"])
     return post

@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db:Annotated[AsyncSession, Depends(get_db)]):
     result = await db.execute(select(models.Post).where(models.Post.id==post_id))
     post = result.scalars().first()

     if not post:
          raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="post not found"
          )
     await db.delete(post)
     await db.commit()
     return None


#normal exception handler
@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
     message=(
          exception.detail
          if exception.detail
          else "an error occured. please check your request and try again"
     )

     if request.url.path.startswith("/api"): # did the req come through a api url
          return await http_exception_handler(request, exception)
     return templates.TemplateResponse(
          request,
          "error.html",
          {
               "status_code": exception.status_code,
               "title": exception.status_code,
               "message":message,
          },
          status_code=exception.status_code,
     )

#validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request:Request, exception:RequestValidationError):
     if request.url.path.startswith("/api/"):
          return await request_validation_exception_handler(request, exception)
     return templates.TemplateResponse(
          request,
          "error.html",
          {
               "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
               "title":status.HTTP_422_UNPROCESSABLE_CONTENT,
               "message":"invalid request. please check input and try again."
          },
          status_code= status.HTTP_422_UNPROCESSABLE_CONTENT
     )