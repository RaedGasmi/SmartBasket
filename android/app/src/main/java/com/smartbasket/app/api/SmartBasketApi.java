package com.smartbasket.app.api;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;
import retrofit2.http.Path;

/** The SmartBasket API endpoints used by the app. */
public interface SmartBasketApi {

    /** Products whose name contains {@code query}; a null query lists products alphabetically. */
    @GET("products")
    Call<List<Product>> searchProducts(@Query("q") String query, @Query("limit") int limit);

    /** The products most often bought in the same basket as the given product, the best first. */
    @GET("products/{id}/bought-together")
    Call<List<Product>> boughtTogether(@Path("id") int productId, @Query("limit") int limit);

    /** Shopping habits of a user; the server answers 404 for an unknown user. */
    @GET("habits/{id}")
    Call<Habits> habits(@Path("id") int userId);

    /** Recommendations for a user; strategy is "reorder" or "discovery". */
    @GET("users/{id}/recommendations")
    Call<Recommendations> recommendations(
            @Path("id") int userId, @Query("strategy") String strategy, @Query("limit") int limit);
}