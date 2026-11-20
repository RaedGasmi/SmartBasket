package com.smartbasket.app.api;

import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

/** Creates the single Retrofit client shared by the whole app. */
public final class ApiClient {

    /** The host machine as seen from the Android emulator; the API listens on port 8000. */
    public static final String BASE_URL = "http://10.0.2.2:8000/";

    private static SmartBasketApi api;

    private ApiClient() {
    }

    /** Returns the shared API client, creating it on first use. */
    public static synchronized SmartBasketApi get() {
        if (api == null) {
            api = new Retrofit.Builder()
                    .baseUrl(BASE_URL)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
                    .create(SmartBasketApi.class);
        }
        return api;
    }
}