package com.smartbasket.app;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.EditText;
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

/** Product list with a search box. */
public class MainActivity extends AppCompatActivity {

    private static final long SEARCH_DELAY_MS = 300;
    private static final int PAGE_SIZE = 50;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ProductAdapter adapter =
            new ProductAdapter(product -> startActivity(ProductDetailActivity.newIntent(this, product)));
    private Call<List<Product>> currentCall;
    private ProgressBar progress;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });

        progress = findViewById(R.id.progress);
        status = findViewById(R.id.status);
        RecyclerView products = findViewById(R.id.products);
        products.setLayoutManager(new LinearLayoutManager(this));
        products.setAdapter(adapter);

        EditText search = findViewById(R.id.search);
        search.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {
            }

            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                scheduleSearch(s.toString().trim());
            }
        });
        findViewById(R.id.for_you).setOnClickListener(view -> startActivity(new Intent(this, ForYouActivity.class)));
        loadProducts("");
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (currentCall != null) {
            currentCall.cancel();
        }
        super.onDestroy();
    }

    /** Waits for a pause in typing before searching, so each keystroke does not send a request. */
    private void scheduleSearch(String query) {
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(() -> loadProducts(query), SEARCH_DELAY_MS);
    }

    /** Loads the products matching {@code query}, cancelling any search still in flight. */
    private void loadProducts(String query) {
        if (currentCall != null) {
            currentCall.cancel();
        }
        progress.setVisibility(View.VISIBLE);
        status.setVisibility(View.GONE);

        currentCall = ApiClient.get().searchProducts(query.isEmpty() ? null : query, PAGE_SIZE);
        currentCall.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<List<Product>> call, @NonNull Response<List<Product>> response) {
                List<Product> body = response.body();
                if (response.isSuccessful() && body != null) {
                    showProducts(body);
                } else {
                    showError(R.string.error_server);
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<Product>> call, @NonNull Throwable error) {
                if (!call.isCanceled()) {
                    showError(R.string.error_network);
                }
            }
        });
    }

    private void showProducts(List<Product> products) {
        progress.setVisibility(View.GONE);
        adapter.submitList(products);
        if (products.isEmpty()) {
            status.setText(R.string.no_products);
            status.setVisibility(View.VISIBLE);
        } else {
            status.setVisibility(View.GONE);
        }
    }

    private void showError(@StringRes int message) {
        progress.setVisibility(View.GONE);
        adapter.submitList(Collections.emptyList());
        status.setText(message);
        status.setVisibility(View.VISIBLE);
    }
}