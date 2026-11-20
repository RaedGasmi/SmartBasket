package com.smartbasket.app.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Recommended products for a user, and the strategy that produced them. */
public class Recommendations {

    private static final String POPULARITY_FALLBACK = "popularity_fallback";

    @SerializedName("strategy")
    private String strategy;

    @SerializedName("items")
    private List<Product> items;

    public List<Product> getItems() {
        return items;
    }

    /** True when the user is unknown and the list is just the most popular products. */
    public boolean isPopularityFallback() {
        return POPULARITY_FALLBACK.equals(strategy);
    }
}