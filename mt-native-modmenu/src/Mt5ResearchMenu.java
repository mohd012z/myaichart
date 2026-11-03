package mt.nativeaddon;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.view.MotionEvent;
import android.widget.CheckBox;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

/** In-app research controls. Does not patch native functions or download market data. */
public final class Mt5ResearchMenu {
    public interface Listener {
        void onLayerChanged(String layer, boolean enabled);
        void onAction(String action);
    }
    private static final String[] LAYERS = {
        "BBMA Dashboard", "Supply & Demand", "Fibonacci",
        "EMA / LWMA", "Bollinger Bands", "Chart Labels"
    };
    private final Context context;
    private final SharedPreferences preferences;
    private final Listener listener;
    private FrameLayout container;
    private LinearLayout panel;
    private float downX, downY, initialX, initialY;

    public Mt5ResearchMenu(Context context, Listener listener) {
        if (context == null || listener == null) throw new IllegalArgumentException("context/listener");
        this.context = context;
        this.listener = listener;
        this.preferences = context.getSharedPreferences("mt5_research_layers_v1", Context.MODE_PRIVATE);
    }

    public void attach(FrameLayout chartContainer) {
        if (chartContainer == null) throw new IllegalArgumentException("chartContainer");
        detach();
        container = chartContainer;
        panel = new LinearLayout(context);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(12), dp(10), dp(12), dp(10));
        panel.setBackgroundColor(Color.argb(238, 18, 26, 40));
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(dp(250), FrameLayout.LayoutParams.WRAP_CONTENT);
        params.leftMargin = dp(12);
        params.topMargin = dp(48);
        container.addView(panel, params);

        TextView header = text("MT5 RESEARCH — DRAG", 16);
        panel.addView(header);
        header.setOnTouchListener((view, event) -> {
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downX = event.getRawX();
                    downY = event.getRawY();
                    initialX = panel.getTranslationX();
                    initialY = panel.getTranslationY();
                    return true;
                case MotionEvent.ACTION_MOVE:
                    float minX = -params.leftMargin;
                    float minY = -params.topMargin;
                    float maxX = Math.max(minX, container.getWidth() - panel.getWidth() - params.leftMargin);
                    float maxY = Math.max(minY, container.getHeight() - panel.getHeight() - params.topMargin);
                    panel.setTranslationX(clamp(initialX + event.getRawX() - downX, minX, maxX));
                    panel.setTranslationY(clamp(initialY + event.getRawY() - downY, minY, maxY));
                    return true;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    return true;
                default:
                    return false;
            }
        });
        for (String layer : LAYERS) {
            CheckBox check = new CheckBox(context);
            check.setText(layer);
            check.setTextColor(Color.WHITE);
            check.setChecked(preferences.getBoolean(layer, false));
            check.setOnCheckedChangeListener((button, enabled) -> {
                preferences.edit().putBoolean(layer, enabled).apply();
                listener.onLayerChanged(layer, enabled);
            });
            panel.addView(check);
        }
        for (String action : new String[]{"Refresh Chart", "Download OHLC", "Export CSV"}) {
            TextView button = text(action, 14);
            button.setPadding(0, dp(8), 0, dp(8));
            button.setOnClickListener(view -> listener.onAction(action));
            panel.addView(button);
        }
    }

    public boolean isEnabled(String layer) { return preferences.getBoolean(layer, false); }
    public void detach() {
        if (panel != null && panel.getParent() instanceof FrameLayout)
            ((FrameLayout) panel.getParent()).removeView(panel);
        panel = null;
        container = null;
    }
    private TextView text(String label, int size) {
        TextView text = new TextView(context);
        text.setText(label);
        text.setTextColor(Color.WHITE);
        text.setTextSize(size);
        return text;
    }
    private int dp(float v) { return (int)(v * context.getResources().getDisplayMetrics().density + 0.5f); }
    private static float clamp(float v, float min, float max) { return Math.max(min, Math.min(max, v)); }
}
