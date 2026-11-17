CREATE SCHEMA IF NOT EXISTS public;

DROP TABLE IF EXISTS 
    public.order_reviews, 
    public.order_payments, 
    public.order_items, 
    public.orders, 
    public.products, 
    public.sellers, 
    public.customers 
CASCADE;


CREATE TABLE IF NOT EXISTS public.customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_unique_id VARCHAR(50) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state VARCHAR(5)
);


CREATE TABLE IF NOT EXISTS public.sellers (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city VARCHAR(100),
    seller_state VARCHAR(5)
);




CREATE TABLE IF NOT EXISTS public.products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_length NUMERIC,
    product_description_length NUMERIC,
    product_photos_qty NUMERIC,
    product_weight_g NUMERIC(10,2),
    product_length_cm NUMERIC(10,2),
    product_height_cm NUMERIC(10,2),
    product_width_cm NUMERIC(10,2)
);


CREATE TABLE IF NOT EXISTS public.orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES public.customers(customer_id),
    order_status VARCHAR(30) NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);


CREATE TABLE IF NOT EXISTS public.order_items (
    order_id VARCHAR(50) NOT NULL REFERENCES public.orders(order_id),
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(50) NOT NULL REFERENCES public.products(product_id),
    seller_id VARCHAR(50) NOT NULL REFERENCES public.sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2) NOT NULL,
    freight_value NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);


CREATE TABLE IF NOT EXISTS public.order_payments (
    order_id VARCHAR(50) NOT NULL REFERENCES public.orders(order_id),
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);


CREATE TABLE IF NOT EXISTS public.order_reviews (
    review_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL REFERENCES public.orders(order_id),
    review_score INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title VARCHAR(255),
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

-- Performance and Foreign Key Indexes
CREATE INDEX IF NOT EXISTS idx_customers_state ON public.customers(customer_state);
CREATE INDEX IF NOT EXISTS idx_customers_city ON public.customers(customer_city);
CREATE INDEX IF NOT EXISTS idx_sellers_state ON public.sellers(seller_state);
CREATE INDEX IF NOT EXISTS idx_sellers_city ON public.sellers(seller_city);
CREATE INDEX IF NOT EXISTS idx_products_category ON public.products(product_category_name);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON public.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp ON public.orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON public.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id ON public.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_order_payments_order_id ON public.order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_order_payments_type ON public.order_payments(payment_type);
CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id ON public.order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_order_reviews_score ON public.order_reviews(review_score);
