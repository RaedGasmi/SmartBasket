package com.smartbasket.app.api;

import com.google.gson.annotations.SerializedName;

import java.util.List;

/** Shopping rhythm and favourite categories of a user. */
public class Habits {

    @SerializedName("n_orders")
    private int orderCount;

    /** Null when the user has a single order. */
    @SerializedName("avg_reorder_interval_days")
    private Double avgReorderIntervalDays;

    @SerializedName("top_categories")
    private List<TopCategory> topCategories;

    public int getOrderCount() {
        return orderCount;
    }

    public Double getAvgReorderIntervalDays() {
        return avgReorderIntervalDays;
    }

    public List<TopCategory> getTopCategories() {
        return topCategories;
    }

    /** A category (aisle) the user buys often. */
    public static class TopCategory {

        @SerializedName("category")
        private String category;

        public String getCategory() {
            return category;
        }
    }
}