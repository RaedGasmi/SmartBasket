package com.smartbasket.app.api;

import com.google.gson.annotations.SerializedName;

/** A product as returned by the SmartBasket API. */
public class Product {

    @SerializedName("product_id")
    private int productId;

    @SerializedName("name")
    private String name;

    @SerializedName("aisle")
    private String aisle;

    @SerializedName("department")
    private String department;

    public int getProductId() {
        return productId;
    }

    public String getName() {
        return name;
    }

    public String getAisle() {
        return aisle;
    }

    public String getDepartment() {
        return department;
    }
}