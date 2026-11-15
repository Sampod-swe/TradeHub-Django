from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
import requests
import uuid
import random
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Product, Comment, UserProfile, Notification, Category, Order, Payment, SellerProfile
from .forms import ProductForm, CommentForm, ProfileForm
from django.core.mail import send_mail
User = get_user_model()


def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    category_slug = request.GET.get('category')

    if category_slug:
        products = products.filter(category__slug=category_slug)

    sort_by = request.GET.get('sort')
    if sort_by == 'low_to_high':
        products = products.order_by('price')
    elif sort_by == 'high_to_low':
        products = products.order_by('-price')

    paginator = Paginator(products, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'categories': categories,
        'selected_category': category_slug,
        'selected_sort': sort_by,
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    comments = product.comments.all().order_by('-created_at')
    comment_form = CommentForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('store:login')

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.product = product
            new_comment.user = request.user
            new_comment.save()
            if product.owner != request.user:
                Notification.objects.create(
                    recipient=product.owner,
                    actor=request.user,
                    product=product,
                    notification_type='comment'
                )
            return redirect('store:product_detail', pk=product.pk)

        context = {
            'product': product,
            'comments': comments,
            'comment_form': comment_form,
        }
        return render(request, 'store/product_detail.html', context)

    context = {
        'product': product,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'store/product_detail.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            if request.user.is_authenticated:
                product.owner = request.user
            product.save()
            return redirect('store:product_list')
    else:
        form = ProductForm()

    return render(request, 'store/product_form.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('store:product_list')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('store:product_list')
        else:
            messages.error(request, 'ইউজারনেম বা পাসওয়ার্ড ভুল দেওয়া হয়েছে!')
        return render(request, 'store/login.html', {'username': username})

    return render(request, 'store/login.html')

def logout_view(request):
    logout(request)
    return redirect('store:product_list')

@login_required
def like_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.likes.filter(id=request.user.id).exists():
        product.likes.remove(request.user)
    else:
        product.likes.add(request.user)
        if product.owner != request.user:
            Notification.objects.create(
                recipient=product.owner,
                actor=request.user,
                product=product,
                notification_type='like'
            )
    return redirect('store:product_detail', pk=pk)

@login_required
def dashboard(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if user.role == 'seller':
        products = Product.objects.filter(owner=user)
    else:
        products = Product.objects.none()

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile সফল ভাবে আপডেট হয়েছে!')
            return redirect('store:dashboard')
    else:
        form = ProfileForm(instance=profile)

    products = Product.objects.filter(owner=request.user)

    context = {
        'form': form,
        'products': products
    }
    return render(request, 'store/dashboard.html', context)

@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('store:dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/product_form.html', {'form': form})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, owner=request.user)
    if request.method == 'POST':
        product.delete()
        return redirect('store:dashboard')
    return render(request, 'store/product_confirm_delete.html', {'product': product})

def product_search(request):
    query = request.GET.get('q', '')
    products = Product.objects.all()
    if query:
        products = products.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    return render(request, 'store/search_results.html', {
        'products': products,
        'query': query
    })

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'store/notification_list.html', {
        'notifications': notifications,
    })

def register_view(request):
    User = get_user_model()
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        address = request.POST.get('address', '').strip()
        role = request.POST.get('role', 'buyer')
        if role not in ('buyer', 'seller'):
            role = 'buyer'

        if User.objects.filter(username=username).exists():
            messages.error(request, 'username টি ব্যাবহার করা হয়েছে!')
            return redirect('store:register')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'email টি ইতিমধ্যে ব্যাবহার করা হয়েছে!')
            return redirect('store:register')

        otp = str(random.randint(100000, 999999))
        request.session['register_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'address': address,
            'otp': otp,
            'role': role,
        }
        send_mail(
            subject='TradeHub-Registration OTP',
            message=f'Your OTP for registration is: {otp}',
            from_email='sampodsweshorma@gmail.com',
            recipient_list=[email],
            fail_silently=False,
        )
        return redirect('store:verify_otp')

    return render(request, 'store/register.html')

def verify_otp(request):
    register_data = request.session.get('register_data')
    if not register_data:
        return redirect('store:register')
    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        if user_otp == register_data['otp']:
            user = User.objects.create_user(
                username=register_data['username'],
                email=register_data['email'],
                password=register_data['password'],
                role=register_data.get('role', 'buyer')
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.address = register_data.get('address', '')
            profile.save()
            user.save()
            del request.session['register_data']
            login(request, user)
            messages.success(request, 'অ্যাকাউন্ট টি তৈরি হয়েছে!')
            return redirect('store:login')
        else:
            messages.error(request, 'ভুল OTP দিয়েছেন! আবার চেষ্টা করুন।')
            return render(request, 'store/verify_otp.html')

    return render(request, 'store/verify_otp.html')

@login_required
def initiate_payment(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    order, created = Order.objects.get_or_create(
        user=request.user,
        is_paid=False,
        defaults={'total_amount': product.price}
    )
    
    if request.method == 'POST':
        selected_method = request.POST.get('payment_method')
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        
        if selected_method == 'bkash':
            return process_bkash_payment(request, order, transaction_id)
        elif selected_method == 'nagad':
            return process_nagad_payment(request, order, transaction_id)
        elif selected_method == 'sslcommerz':
            return process_sslcommerz_payment(request, order, transaction_id)

    return render(request, 'store/checkout.html', {'order': order, 'product': product})


def process_bkash_payment(request, order, transaction_id):
    callback_url = (
        f"http://127.0.0.1:8000/payment/callback/?"
        f"order_id={order.id}&method=bkash&trx_id={transaction_id}&status=success"
    )
    headers = {
        'Content-Type': 'application/json',
        'x-app-key': getattr(settings, 'BKASH_APP_KEY', ''),
    }
    data = {
        'mode': '0011',
        'payerReference': request.user.username,
        'callbackURL': callback_url,
        'amount': str(order.total_amount),
        'currency': 'BDT',
        'intent': 'sale',
        'merchantInvoiceNumber': f'INV-{order.id}-{transaction_id}',
    }
    try:
        response = requests.post(f'{settings.BKASH_URL}', headers=headers, json=data, timeout=20)
        response.raise_for_status()
        res_data = response.json()
    except (requests.RequestException, ValueError):
        res_data = {}

    if res_data.get('bkashURL'):
        return redirect(res_data['bkashURL'])

    return redirect(callback_url)


def process_nagad_payment(request, order, transaction_id):
    callback_url = (
        f"http://127.0.0.1:8000/payment/callback/?"
        f"order_id={order.id}&method=nagad&trx_id={transaction_id}&status=success"
    )
    nagad_checkout_url = getattr(settings, 'NAGAD_URL', 'https://sandbox.nagad.com.bd')
    return redirect(f'{nagad_checkout_url}/checkout/initialize?order_id={order.id}&trx_id={transaction_id}&next={callback_url}')


def process_sslcommerz_payment(request, order, transaction_id):
    callback_url = (
        f"http://127.0.0.1:8000/payment/callback/?"
        f"order_id={order.id}&method=sslcommerz&trx_id={transaction_id}&status=success"
    )
    return redirect(
        'https://sandbox.sslcommerz.com/gwprocess/v4/api.php?'
        f'order_id={order.id}&trx_id={transaction_id}&amount={order.total_amount}&callback={callback_url}'
    )


@csrf_exempt
def payment_callback(request):
    status = request.GET.get('status')
    order_id = request.GET.get('order_id')
    method = request.GET.get('method') or 'unknown'
    trx_id = request.GET.get('trx_id') or 'TRX99887766'

    if not order_id:
        return render(request, 'store/payment_failed.html')

    order = get_object_or_404(Order, id=order_id)

    if status == 'success':
        Payment.objects.create(
            order=order,
            user=order.user,
            method=method,
            amount=order.total_amount,
            transection_id=trx_id,
            status=True,
        )
        order.is_paid = True
        order.save()
        return render(request, 'store/payment_success.html', {'order': order})

    return render(request, 'store/payment_failed.html', {'order': order})