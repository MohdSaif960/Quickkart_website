from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# ----------------------------
# Category Model
# ----------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



# ----------------------------
# Product Model
# ----------------------------
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/")
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔹 Naya field
    brand = models.CharField(max_length=100, default="Unknown")

    # 🔹 Size options (comma separated string: "S,M,L,XL")
    sizes = models.CharField(max_length=100, blank=True, help_text="Comma separated sizes (e.g. S,M,L,XL)")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def final_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def discount_percent(self):
        """Return discount percentage (integer)"""
        if self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    # 🔹 Sizes ko list me convert karne ka helper
    def get_size_list(self):
        return [s.strip() for s in self.sizes.split(",") if s.strip()]


# ----------------------------
# Cart Model
# ----------------------------
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


# ----------------------------
# CartItem Model
# ----------------------------
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    # 🔹 Size field (user jo select karega)
    size = models.CharField(max_length=10, blank=True, null=True)
    image = models.ImageField(upload_to="cartitem/", null=True, blank=True)

    def save(self, *args, **kwargs):
        # Agar CartItem me image nahi hai, product image se copy karo
        if not self.image and self.product.image:
            self.image = self.product.image
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.size or 'No size'})"

    @property
    def total_price(self):
        return self.quantity * self.product.final_price


# ----------------------------
# Address Model
# ----------------------------
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    landmark = models.CharField(max_length=200, blank=True)
    address_line = models.TextField()

    def __str__(self):
        return f"{self.full_name}, {self.city}"


# ----------------------------
# Order Model
# ----------------------------
class Order(models.Model):
    STATUS_CHOICES = [
        #("Pending", "Pending"),
        ("Placed", "Placed"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Placed")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


# ----------------------------
# OrderItem Model
# ----------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # 🔹 Size field (user jo select karega)
    size = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        # Agar product None ho to "Unknown Product" return karo
        if self.product:
            return f"{self.product.name} ({self.size}) x {self.quantity}"
        else:
            return f"{self.quantity} x Unknown Product"

    @property
    def total_price(self):
        return self.quantity * self.price

# ----------------------------
# Payment Model (Optional but recommended)
# ----------------------------
class Payment(models.Model):
    PAYMENT_METHODS = [
        ("COD", "Cash on Delivery"),
        ("CARD", "Credit/Debit Card"),
        ("UPI", "UPI"),
        ("NETBANKING", "Net Banking"),
        ("WALLET", "Wallet"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Order {self.order.id} via {self.method}"
