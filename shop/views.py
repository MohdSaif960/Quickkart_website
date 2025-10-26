from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, Product, Cart, CartItem, Address, Order, OrderItem, Payment
from django.contrib.auth.models import User

# ----------------------------
# Home Page – Show all products
# ----------------------------
def home_view(request):
    products = Product.objects.all().order_by('-created_at')
    #products = Product.objects.all()
    categories = Category.objects.all()

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = sum(item.quantity for item in cart.items.all())

    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        "cart_count": cart_count
    })

def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category)

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = sum(item.quantity for item in cart.items.all())

    return render(request, 'shop/category_products.html', {
        'category': category,
        'products': products,
        "cart_count": cart_count,
    })




# ----------------------------
# Product Detail Page
# ----------------------------
def product_detail_view(request, id):
    # Current product
    product = get_object_or_404(Product, id=id)

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = sum(item.quantity for item in cart.items.all())

    # Related products: same category wale, current product ko exclude karo
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:20]

    # 🔹 product.get_size_list() se sizes bhejna
    sizes = product.get_size_list()

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related_products': related_products,
        "cart_count": cart_count,
        "sizes": sizes   # ✅ naya
    })



# ----------------------------
# Cart Page
# ----------------------------
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.all()

    # Total product price (sum of all product final_price * quantity)
    total_price = sum(item.product.price * item.quantity for item in items)

    # Total discounts (sum of discount per item)
    total_discount = sum(
        ((item.product.price - item.product.final_price) * item.quantity)
        for item in items
    )

    # Order total
    order_total = total_price - total_discount

    # ----------------------------
    # Related products logic
    # ----------------------------
    # Example: show 8 random products excluding ones already in cart
    cart_product_ids = items.values_list('product__id', flat=True)
    related_products = Product.objects.exclude(id__in=cart_product_ids)[:20]

    # Context
    context = {
        'cart': cart,
        'items': items,
        'total_price': total_price,
        'total_discount': total_discount,
        'total': order_total,  # use this in template for "Order Total"
        'related_products': related_products,  # 👈 added
    }

    return render(request, 'shop/cart.html', context)

# ----------------------------
# Add to Cart
# ----------------------------

from django.http import JsonResponse
def add_to_cart_view(request, product_id):
    if not request.user.is_authenticated:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "Please login before adding items to cart."}, status=401)
        messages.warning(request, "Please login before adding items to cart.", extra_tags="detail")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    product = get_object_or_404(Product, id=product_id)

    if product.stock <= 0:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "Sorry, this product is out of stock."}, status=400)
        messages.error(request, "Sorry, this product is out of stock.", extra_tags="detail")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    cart, created = Cart.objects.get_or_create(user=request.user)

    selected_size = request.POST.get("size")
    quantity = int(request.POST.get("quantity", 1))

    # Try to get existing CartItem for same product
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()

    if cart_item:
        new_qty = cart_item.quantity + quantity
        if new_qty <= product.stock:
            cart_item.quantity = new_qty
            if selected_size:
                cart_item.size = selected_size
            cart_item.save()
            message_text = f"{product.name} added to cart (x{cart_item.quantity})."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": message_text}, status=200)
            messages.success(request, message_text, extra_tags="detail")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
        else:
            # ✅ Stock limit message
            error_msg = f"Not enough stock. Only {product.stock} left."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg, extra_tags="detail")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
    else:
        if quantity > product.stock:
            # ✅ Agar new item hai aur requested qty zyada hai
            error_msg = f"Not enough stock. Only {product.stock} left."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg, extra_tags="detail")
            return redirect(request.META.get('HTTP_REFERER', 'home'))

        # Save with requested quantity
        CartItem.objects.create(cart=cart, product=product, quantity=quantity, size=selected_size)
        message_text = f"{product.name} added to cart (x{quantity})."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": message_text}, status=200)
        messages.success(request, message_text, extra_tags="detail")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

# ----------------------------
# Update Cart Item
# ----------------------------
@login_required
def update_cart_item_view(request, item_id):
    # 🔹 Safe check: agar item delete ho chuka ho to 404 na aaye
    item = CartItem.objects.filter(id=item_id, cart__user=request.user).first()
    if not item:
        messages.error(request, "Item no longer in cart.")
        return redirect('cart')

    if request.method == 'POST':
        # Check if remove button was clicked
        if 'remove_item' in request.POST:
            item.delete()
            messages.info(request, f"{item.product.name} removed from cart.")

        else:
            # Update quantity
            quantity = int(request.POST.get('quantity', 1))
            if quantity > 0:
                # ✅ Stock check
                if quantity <= item.product.stock:
                    item.quantity = quantity

                    # ✅ Update size (agar user ne select kiya hai)
                    size = request.POST.get('size')
                    if size:
                        item.size = size

                    item.save()
                    messages.success(request, "Cart updated.")
                else:
                    # 🔹 Stock message with number (existing change)
                    messages.error(request,
                        f"Not enough stock available. Only {item.product.stock} left."
                    )
            else:
                item.delete()
                messages.info(request, f"{item.product.name} removed from cart.")

    return redirect('cart')


# ----------------------------
# Checkout Page
# ----------------------------
"""@login_required
def checkout_view(request):
    cart = get_object_or_404(Cart, user=request.user)
    addresses = Address.objects.filter(user=request.user)
    items = cart.items.all()
    total = sum(item.total_price for item in items)
    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'items': items,
        'addresses': addresses,
        'total': total
    })"""
@login_required
def checkout_view(request):
    product_id = request.GET.get("product_id")
    addresses = Address.objects.filter(user=request.user)

    if product_id:
        # ✅ Buy Now flow
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.GET.get("quantity", 1))   # ✅ yaha se quantity le
        size = request.GET.get("size")  # ✅ size from query param

        # 🔹 Stock check
        if quantity > product.stock:
            messages.error(request, f"Not enough stock. Only {product.stock} left.")
            quantity = product.stock  # optional: limit quantity to stock
            #return redirect('checkout')

        price = product.discount_price or product.price
        total = price * quantity

        return render(request, 'shop/checkout.html', {
            'single_product': product,
            'single_quantity': quantity,   # ✅ clear name so cart flow me clash na ho
            'addresses': addresses,
            'total': total,
            'single_size': size
        })

    # ✅ Normal cart checkout
    cart = get_object_or_404(Cart, user=request.user)
    items = cart.items.all()
    total = sum(item.total_price for item in items)

    return render(request, 'shop/checkout.html', {
        'cart': cart,
        'items': items,
        'addresses': addresses,
        'total': total
    })

# ----------------------------
# Add Address
# ----------------------------
@login_required
def address_add_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        pincode = request.POST.get('pincode')
        city = request.POST.get('city')
        state = request.POST.get('state')
        landmark = request.POST.get('landmark')
        address_line = request.POST.get('address_line')
        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone_number=phone_number,
            pincode=pincode,
            city=city,
            state=state,
            landmark=landmark,
            address_line=address_line
        )
        messages.success(request, "Address added.")
        return redirect('checkout')
    return render(request, 'shop/address_add.html')





# ----------------------------
# Update Address
# ----------------------------
@login_required
def address_update_view(request, pk):
    # ensure only owner can edit
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'POST':
        # get updated values from form
        address.full_name = request.POST.get('full_name')
        address.phone_number = request.POST.get('phone_number')
        address.pincode = request.POST.get('pincode')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.landmark = request.POST.get('landmark')
        address.address_line = request.POST.get('address_line')

        address.save()
        messages.success(request, "Address updated.")
        return redirect('checkout')   # ya jahan redirect karna chahte ho

    # GET -> show form with existing data (reuse same template or separate)
    return render(request, 'shop/update.html', {'address': address})



# ----------------------------
# Place Order
# ----------------------------
from django.core.mail import send_mail
from django.conf import settings

@login_required
def place_order_view(request):
    if request.method == 'POST':
        address_id = int(request.POST.get('address'))
        address = get_object_or_404(Address, id=address_id, user=request.user)

        product_id = request.POST.get('product_id')  # check if Buy Now hai
        size = request.POST.get('size')  # ✅ size receive
        quantity = int(request.POST.get('quantity', 1))  # ✅ get actual quantity

        if product_id:
            # ----------------------------
            # Buy Now Flow
            # ----------------------------
            product = get_object_or_404(Product, id=product_id)

            # ✅ stock check
            if product.stock < 1:
                messages.error(request, f"Sorry, {product.name} is out of stock.")
                return redirect('checkout')

            # ✅ order create
            order = Order.objects.create(
                user=request.user,
                address=address,
                total_amount=product.final_price * quantity
            )

            # ✅ order item create
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,  # Buy Now = single product
                price=product.final_price,
                size=size # ✅ Added size
            )

            # ✅ stock reduce
            product.stock -=  quantity   # ✔️ ab jitna order hua utna kam hoga
            product.save()

            # ----------------------------
            # SEND EMAIL NOTIFICATION
            # ----------------------------
            subject = f"New Order by {request.user.username} - Order ID #{order.id}"
            message = f"User: {request.user.username}\nEmail: {request.user.email}\nProduct: {product.name}\nQuantity: {quantity}\nSize: {size}\nTotal Amount: {order.total_amount}"
            recipient_list = ['mohdsaif88824923@gmail.com']  # yaha apna email daalo
            send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)

            messages.success(request, "Order placed successfully!")
            return redirect('order_success', order_id=order.id)

        else:
            # ----------------------------
            # Normal Cart Flow
            # ----------------------------
            cart = get_object_or_404(Cart, user=request.user)
            items = cart.items.all()
            total = sum(item.total_price for item in items)

            # ✅ order create
            order = Order.objects.create(
                user=request.user,
                address=address,
                total_amount=total * quantity
            )

            for item in items:
                # ✅ stock check
                if item.product.stock < item.quantity:
                    messages.error(request, f"Not enough stock for {item.product.name}.")
                    order.delete()  # agar stock kam hai to order cancel kar do
                    return redirect('checkout')

                # ✅ order item create
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.final_price,
                    size = item.size  # ✅ Added size from CartItem
                )

                # ✅ stock reduce
                item.product.stock -= item.quantity
                item.product.save()

            # ----------------------------
            # SEND EMAIL NOTIFICATION FOR CART ORDERS
            # ----------------------------
            subject = f"New Order by {request.user.username} - Order ID #{order.id}"
            message = f"User: {request.user.username}\nEmail: {request.user.email}\nTotal Amount: {order.total_amount}\nProducts:\n"
            for item in items:
                message += f"- {item.product.name} | Quantity: {item.quantity} | Size: {item.size}\n"
            recipient_list = ['mohdsaif88824923@gmail.com']  # yaha apna email daalo
            send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)

            # ✅ cart empty
            cart.items.all().delete()
            messages.success(request, "Order placed successfully!")
            return redirect('order_success', order_id=order.id)

    return redirect('checkout')


# ----------------------------
# Order Success Page
# ----------------------------
@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'shop/order_success.html', {'order': order})


# ----------------------------
# Orders List Page
# ----------------------------
@login_required
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/orders.html', {'orders': orders})



@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Pehle items fetch karo
    items = order.items.all()

    # Total product price (per item price * quantity)
    total_price = sum(item.product.price * item.quantity for item in items)

    # Total discounts (price - final_price) * quantity
    total_discount = sum(
        ((item.product.price - item.product.final_price) * item.quantity)
        for item in items
    )

    # Order total
    order_total = total_price - total_discount

    # All possible steps
    steps = ["Placed", "Shipped", "Delivered"]

    step_status = []

    if order.status == "Cancelled":
        # If cancelled, show steps till Placed and then Cancelled
        step_status.append({"name": "Pending", "status": "completed"})
        step_status.append({"name": "Placed", "status": "completed"})
        step_status.append({"name": "Cancelled", "status": "cancelled"})
    else:
        reached_current = False
        for s in steps:
            if s == order.status:
                step_status.append({"name": s, "status": "active"})
                reached_current = True
            elif not reached_current:
                step_status.append({"name": s, "status": "completed"})
            else:
                step_status.append({"name": s, "status": "pending"})

    return render(request, "shop/order_detail.html", {
        "order": order,
        "step_status": step_status,
        "items": items,  # template me bhi use kar sakte ho
        "total_price": total_price,
        "total_discount": total_discount,
        "total": order_total
    })













from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
#from django.contrib import messages
from .forms import SignUpForm, LoginForm
from django.contrib.auth.decorators import login_required

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'shop/signup.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'shop/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'shop/profile.html', {'user': request.user})







from django.db.models import Q

def search_products(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category_id')  # ✅ category catch

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = sum(item.quantity for item in cart.items.all())

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ) if query else Product.objects.none()

    # ✅ अगर category_id मौजूद है तो सिर्फ उसी category में search होगा
    if category_id:
        products = products.filter(category_id=category_id)

    return render(request, 'shop/search_results.html', {
        'query': query,
        'products': products,
        "cart_count": cart_count
    })
