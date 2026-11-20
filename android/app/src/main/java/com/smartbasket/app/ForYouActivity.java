package com.smartbasket.app;

import android.os.Bundle;
import android.text.TextUtils;
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

import com.google.android.material.button.MaterialButtonToggleGroup;
import com.smartbasket.app.api.ApiClient;
import com.smartbasket.app.api.Habits;
import com.smartbasket.app.api.Recommendations;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/** Shopping habits and personalised recommendations for the demo user. */
public class ForYouActivity extends AppCompatActivity {

    /** The MVP has no login: the screen always shows this user of the Instacart sample. */
    private static final int DEMO_USER_ID = 1;
    private static final int LIST_LIMIT = 10;
    private static final String STRATEGY_REORDER = "reorder";
    private static final String STRATEGY_DISCOVERY = "discovery";

    private final ProductAdapter adapter =
            new ProductAdapter(product -> startActivity(ProductDetailActivity.newIntent(this, product)));
    private Call<Habits> habitsCall;
    private Call<Recommendations> recommendationsCall;
    private TextView habitsView;
    private TextView note;
    private TextView status;
    private ProgressBar progress;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_for_you);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (view, insets) -> {
            Insets bars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            return insets;
        });

        habitsView = findViewById(R.id.habits);
        note = findViewById(R.id.note);
        status = findViewById(R.id.status);
        progress = findViewById(R.id.progress);
        RecyclerView list = findViewById(R.id.recommendations);
        list.setLayoutManager(new LinearLayoutManager(this));
        list.setAdapter(adapter);

        MaterialButtonToggleGroup toggle = findViewById(R.id.toggle);
        toggle.addOnButtonCheckedListener((group, checkedId, isChecked) -> {
            if (isChecked) {
                loadRecommendations(checkedId == R.id.discovery ? STRATEGY_DISCOVERY : STRATEGY_REORDER);
            }
        });

        loadHabits();
        toggle.check(R.id.reorder);
    }

    @Override
    protected void onDestroy() {
        if (habitsCall != null) {
            habitsCall.cancel();
        }
        if (recommendationsCall != null) {
            recommendationsCall.cancel();
        }
        super.onDestroy();
    }

    private void loadHabits() {
        habitsCall = ApiClient.get().habits(DEMO_USER_ID);
        habitsCall.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<Habits> call, @NonNull Response<Habits> response) {
                Habits body = response.body();
                if (response.isSuccessful() && body != null) {
                    showHabits(body);
                } else if (response.code() == 404) {
                    habitsView.setText(R.string.no_history);
                } else {
                    habitsView.setText(R.string.error_server);
                }
            }

            @Override
            public void onFailure(@NonNull Call<Habits> call, @NonNull Throwable error) {
                if (!call.isCanceled()) {
                    habitsView.setText(R.string.error_network);
                }
            }
        });
    }

    private void showHabits(Habits habits) {
        int orders = habits.getOrderCount();
        String summary = getResources().getQuantityString(R.plurals.habits_orders, orders, orders);
        Double interval = habits.getAvgReorderIntervalDays();
        if (interval != null) {
            summary = getString(R.string.habits_orders_interval, summary, interval);
        }
        List<String> categories = new ArrayList<>();
        for (Habits.TopCategory category : habits.getTopCategories()) {
            categories.add(category.getCategory());
        }
        if (!categories.isEmpty()) {
            summary += "\n" + getString(R.string.habits_categories, TextUtils.join(", ", categories));
        }
        habitsView.setText(summary);
    }

    /** Loads one recommendation list, cancelling the other one if it is still in flight. */
    private void loadRecommendations(String strategy) {
        if (recommendationsCall != null) {
            recommendationsCall.cancel();
        }
        progress.setVisibility(View.VISIBLE);
        status.setVisibility(View.GONE);

        recommendationsCall = ApiClient.get().recommendations(DEMO_USER_ID, strategy, LIST_LIMIT);
        recommendationsCall.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<Recommendations> call, @NonNull Response<Recommendations> response) {
                Recommendations body = response.body();
                if (response.isSuccessful() && body != null) {
                    showRecommendations(body);
                } else {
                    showError(R.string.error_server);
                }
            }

            @Override
            public void onFailure(@NonNull Call<Recommendations> call, @NonNull Throwable error) {
                if (!call.isCanceled()) {
                    showError(R.string.error_network);
                }
            }
        });
    }

    private void showRecommendations(Recommendations result) {
        progress.setVisibility(View.GONE);
        note.setVisibility(result.isPopularityFallback() ? View.VISIBLE : View.GONE);
        adapter.submitList(result.getItems());
        if (result.getItems().isEmpty()) {
            status.setText(R.string.no_products);
            status.setVisibility(View.VISIBLE);
        } else {
            status.setVisibility(View.GONE);
        }
    }

    private void showError(@StringRes int message) {
        progress.setVisibility(View.GONE);
        note.setVisibility(View.GONE);
        adapter.submitList(Collections.emptyList());
        status.setText(message);
        status.setVisibility(View.VISIBLE);
    }
}