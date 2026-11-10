CREATE SCHEMA IF NOT EXISTS public;

CREATE TABLE IF NOT EXISTS public.users (
    user_id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    city VARCHAR(100),
    province VARCHAR(50),
    user_type VARCHAR(20) NOT NULL,
    signup_date DATE,
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS public.vehicles (
    vehicle_id INTEGER PRIMARY KEY,
    driver_id INTEGER NOT NULL REFERENCES public.users(user_id),
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    license_plate VARCHAR(20) UNIQUE,
    color VARCHAR(30),
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS public.rides (
    ride_id INTEGER PRIMARY KEY,
    rider_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    requested_at TIMESTAMP,
    pickup_time TIMESTAMP,
    dropoff_time TIMESTAMP,
    pickup_latitude DECIMAL(9,6),
    pickup_longitude DECIMAL(9,6),
    dropoff_latitude DECIMAL(9,6),
    dropoff_longitude DECIMAL(9,6),
    distance_km DECIMAL(10,2),
    fare DECIMAL(10,2),
    surge_multiplier DECIMAL(3,2),
    status VARCHAR(30),
    cancellation_reason VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS public.payments (
    payment_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL REFERENCES public.rides(ride_id),
    user_id INTEGER NOT NULL REFERENCES public.users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(30),
    payment_status VARCHAR(30),
    transaction_id VARCHAR(100),
    payment_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.ratings (
    rating_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL REFERENCES public.rides(ride_id),
    rider_id INTEGER NOT NULL REFERENCES public.users(user_id),
    driver_id INTEGER NOT NULL REFERENCES public.users(user_id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    rated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vehicles_driver_id
    ON public.vehicles(driver_id);
CREATE INDEX IF NOT EXISTS idx_rides_rider_id
    ON public.rides(rider_id);
CREATE INDEX IF NOT EXISTS idx_rides_driver_id
    ON public.rides(driver_id);
CREATE INDEX IF NOT EXISTS idx_rides_requested_at
    ON public.rides(requested_at);
CREATE INDEX IF NOT EXISTS idx_rides_status
    ON public.rides(status);
CREATE INDEX IF NOT EXISTS idx_payments_ride_id
    ON public.payments(ride_id);
CREATE INDEX IF NOT EXISTS idx_payments_user_id
    ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_ride_id
    ON public.ratings(ride_id);
CREATE INDEX IF NOT EXISTS idx_ratings_driver_id
    ON public.ratings(driver_id);
