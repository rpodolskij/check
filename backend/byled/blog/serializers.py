from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Post, Comment, Categories


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer()

    class Meta:
        model = Post
        depth = 1
        fields = '__all__'


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        exclude = ['author', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text']


class CategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = '__all__'


class CategoriesCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ['title', 'picture']
