package com.smartbasket.app;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.DiffUtil;
import androidx.recyclerview.widget.ListAdapter;
import androidx.recyclerview.widget.RecyclerView;

import com.smartbasket.app.api.Product;

import java.util.Objects;

/** Shows products as a two-line list: the name, then the aisle and department. */
public class ProductAdapter extends ListAdapter<Product, ProductAdapter.ViewHolder> {

    /** Called when a product row is tapped. */
    public interface OnProductClickListener {
        void onProductClick(Product product);
    }

    private static final DiffUtil.ItemCallback<Product> DIFF = new DiffUtil.ItemCallback<>() {
        @Override
        public boolean areItemsTheSame(@NonNull Product oldItem, @NonNull Product newItem) {
            return oldItem.getProductId() == newItem.getProductId();
        }

        @Override
        public boolean areContentsTheSame(@NonNull Product oldItem, @NonNull Product newItem) {
            return Objects.equals(oldItem.getName(), newItem.getName())
                    && Objects.equals(oldItem.getAisle(), newItem.getAisle())
                    && Objects.equals(oldItem.getDepartment(), newItem.getDepartment());
        }
    };

    private final OnProductClickListener listener;

    public ProductAdapter(OnProductClickListener listener) {
        super(DIFF);
        this.listener = listener;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_product, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        Product product = getItem(position);
        holder.name.setText(product.getName());
        holder.details.setText(holder.itemView.getContext()
                .getString(R.string.product_details, product.getAisle(), product.getDepartment()));
        holder.itemView.setOnClickListener(view -> listener.onProductClick(product));
    }

    /** Holds the two text views of one list row. */
    static class ViewHolder extends RecyclerView.ViewHolder {
        final TextView name;
        final TextView details;

        ViewHolder(@NonNull View itemView) {
            super(itemView);
            name = itemView.findViewById(R.id.name);
            details = itemView.findViewById(R.id.details);
        }
    }
}