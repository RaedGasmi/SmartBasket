package com.smartbasket.app;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.annotation.StringRes;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.smartbasket.app.api.ApiClient;
import com.smartbasket.app.api.Product;

import java.util.Collections;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/** One product, with the products most often bought together with it. */
public class ProductDetailActivity extends AppCompatActivity {

    private static final String EXTRA_ID = "product_id";
    private static final String EXTRA_NAME = "product_name";
    private static final String EXTRA_AISLE = "product_aisle";
    private static final String EXTRA_DEPARTMENT = "product_department";
    private static final int RELATED_LIMIT = 10;

    private final ProductAdapter adapter =
            new ProductAdapter(product -> startActivity(newIntent(this, product)));
    private Call<List<Product>> currentCall;
    private ProgressBar progress;
    private TextView status;

    /** Creates the intent that opens the detail screen of {@code product}. */
    public static Intent newIntent(Context context, Product product) {
        return new Intent(context, ProductDetailActivity.class)
                .putExtra(EXTRA_ID, product.getProductId())
                .putExtra(EXTRA_NAME, product.getName())
                .putExtra(EXTRA_AISLE, product.getAisle())
                .putExtra(EXTRA_DEPARTMENT, product.getDepartment());
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_product_detail);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });

        Intent intent = getIntent();
        ((TextView) findViewById(R.id.name)).setText(intent.getStringExtra(EXTRA_NAME));
        ((TextView) findViewById(R.id.details)).setText(getString(R.string.product_details,
                intent.getStringExtra(EXTRA_AISLE), intent.getStringExtra(EXTRA_DEPARTMENT)));

        progress = findViewById(R.id.progress);
        status = findViewById(R.id.status);
        RecyclerView related = findViewById(R.id.related);
        related.setLayoutManager(new LinearLayoutManager(this));
        related.setAdapter(adapter);

        loadBoughtTogether(intent.getIntExtra(EXTRA_ID, -1));
    }

    @Override
    protected void onDestroy() {
        if (currentCall != null) {
            currentCall.cancel();
        }
        super.onDestroy();
    }

    private void loadBoughtTogether(int productId) {
        progress.setVisibility(View.VISIBLE);
        status.setVisibility(View.GONE);

        currentCall = ApiClient.get().boughtTogether(productId, RELATED_LIMIT);
        currentCall.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<List<Product>> call, @NonNull Response<List<Product>> response) {
                List<Product> body = response.body();
                if (response.isSuccessful() && body != null) {
                    showProducts(body);
                } else {
                    showMessage(R.string.error_server);
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<Product>> call, @NonNull Throwable error) {
                if (!call.isCanceled()) {
                    showMessage(R.string.error_network);
                }
            }
        });
    }

    private void showProducts(List<Product> products) {
        adapter.submitList(products);
        if (products.isEmpty()) {
            showMessage(R.string.no_bought_together);
        } else {
            progress.setVisibility(View.GONE);
            status.setVisibility(View.GONE);
        }
    }

    private void showMessage(@StringRes int message) {
        progress.setVisibility(View.GONE);
        if (message != R.string.no_bought_together) {
            adapter.submitList(Collections.emptyList());
        }
        status.setText(message);
        status.setVisibility(View.VISIBLE);
    }
}