from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('product/<int:id>/', views.product_detail_view, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item_view, name='update_cart_item'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('address/add/', views.address_add_view, name='address_add'),
    path('address/<int:pk>/edit/', views.address_update_view, name='address_update'),  # << add this

    path('place_order/', views.place_order_view, name='place_order'),
    path('order/success/<int:order_id>/', views.order_success_view, name='order_success'),
    path('orders/', views.order_list_view, name='order_list'),
    path('order/<int:order_id>/', views.order_detail_view, name='order_detail'),

    path('search/', views.search_products, name='search'),


    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
