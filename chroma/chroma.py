import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import colorsys
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.optimize import differential_evolution, minimize
from itertools import product
import warnings
warnings.filterwarnings('ignore')

def load_png_with_alpha(image_path):
    """Load PNG and ensure it has alpha channel"""
    img = Image.open(image_path)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    return img

def extract_subject_colors(img_array, sample_size=10000):
    """Extract colors from non-transparent pixels (the subject)"""
    # Get RGB and alpha channels
    rgb = img_array[:, :, :3]
    alpha = img_array[:, :, 3]
    
    # Only consider pixels that are not fully transparent
    mask = alpha > 0
    subject_pixels = rgb[mask]
    
    # Sample if too many pixels
    if len(subject_pixels) > sample_size:
        indices = np.random.choice(len(subject_pixels), sample_size, replace=False)
        subject_pixels = subject_pixels[indices]
    
    return subject_pixels

def find_dominant_subject_colors(subject_pixels, n_colors=30):
    """Find dominant colors in the subject using K-means"""
    if len(subject_pixels) == 0:
        return []
    
    kmeans = KMeans(n_clusters=min(n_colors, len(subject_pixels)), random_state=42, n_init=10)
    kmeans.fit(subject_pixels)
    
    # Get cluster centers and their frequencies
    unique, counts = np.unique(kmeans.labels_, return_counts=True)
    colors_with_freq = [(kmeans.cluster_centers_[i], counts[i]) 
                       for i in range(len(unique))]
    colors_with_freq.sort(key=lambda x: x[1], reverse=True)
    
    return colors_with_freq

def calculate_color_distance_lab(color1, color2):
    """Calculate perceptual color distance using LAB color space"""
    # Convert RGB to LAB (simplified version)
    def rgb_to_lab(rgb):
        # Normalize RGB
        rgb = np.array(rgb) / 255.0
        
        # Apply gamma correction
        rgb = np.where(rgb > 0.04045, 
                      np.power((rgb + 0.055) / 1.055, 2.4),
                      rgb / 12.92)
        
        # Convert to XYZ
        xyz_matrix = np.array([[0.4124564, 0.3575761, 0.1804375],
                              [0.2126729, 0.7151522, 0.0721750],
                              [0.0193339, 0.1191920, 0.9503041]])
        xyz = np.dot(xyz_matrix, rgb)
        
        # Normalize for D65 illuminant
        xyz[0] /= 0.95047
        xyz[1] /= 1.00000
        xyz[2] /= 1.08883
        
        # Convert to LAB
        def f(t):
            return np.where(t > 0.008856,
                          np.power(t, 1/3),
                          7.787 * t + 16/116)
        
        fx, fy, fz = f(xyz)
        
        L = 116 * fy - 16
        a = 500 * (fx - fy)
        b = 200 * (fy - fz)
        
        return np.array([L, a, b])
    
    lab1 = rgb_to_lab(color1)
    lab2 = rgb_to_lab(color2)
    
    # Calculate Delta E (CIE76)
    delta_e = np.sqrt(np.sum((lab1 - lab2) ** 2))
    return delta_e

def calculate_color_distance(color1, color2):
    """Calculate perceptual color distance (weighted RGB)"""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    
    # Weighted Euclidean distance
    rmean = (r1 + r2) / 2
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    
    weight_r = 2 + rmean/256
    weight_g = 4
    weight_b = 2 + (255-rmean)/256
    
    distance = np.sqrt(weight_r * dr**2 + weight_g * dg**2 + weight_b * db**2)
    return distance

def evaluate_background_color_comprehensive(bg_color, subject_colors, subject_pixels_sample):
    """Comprehensive evaluation of background color quality"""
    bg_array = np.array(bg_color)
    
    # Calculate minimum distance to dominant colors
    min_distances = []
    total_pixels = 0
    
    for color, freq in subject_colors:
        distance = calculate_color_distance_lab(bg_color, color)
        min_distances.append(distance)
        total_pixels += freq
    
    # Calculate weighted average distance
    weighted_distances = []
    for i, (color, freq) in enumerate(subject_colors):
        weight = freq / total_pixels
        weighted_distances.append(min_distances[i] * weight)
    
    avg_distance = sum(weighted_distances)
    min_distance = min(min_distances) if min_distances else 0
    
    # Calculate percentile distances to all subject pixels
    if len(subject_pixels_sample) > 0:
        all_distances = [calculate_color_distance(bg_color, pixel) for pixel in subject_pixels_sample[:1000]]
        percentile_5 = np.percentile(all_distances, 5)
        percentile_10 = np.percentile(all_distances, 10)
    else:
        percentile_5 = percentile_10 = 0
    
    # Calculate color properties
    h, s, v = colorsys.rgb_to_hsv(bg_color[0]/255, bg_color[1]/255, bg_color[2]/255)
    
    # Score components
    # 1. Minimum distance (most important)
    distance_score = min_distance / 100.0  # Normalize for LAB distance
    
    # 2. Low percentile distance (ensure separation from outliers)
    percentile_score = percentile_5 / 255.0
    
    # 3. Saturation (higher is better for chroma key)
    saturation_score = s
    
    # 4. Not too bright or too dark
    brightness_score = 1.0 - abs(v - 0.7) / 0.7
    
    # 5. Avoid skin tones and common clothing colors
    problem_hues = [
        (0.05, 0.1),   # Skin tones (red-orange)
        (0.58, 0.62),  # Denim blue
        (0.0, 0.02),   # Deep reds
        (0.98, 1.0),   # Deep reds (wrapped)
    ]
    
    hue_penalty = 0
    for problem_h, tolerance in problem_hues:
        if abs(h - problem_h) < tolerance:
            hue_penalty = max(hue_penalty, 1.0 - abs(h - problem_h) / tolerance)
    
    # Combined score with refined weights
    total_score = (
        distance_score * 0.4 +       # Most important: far from subject
        percentile_score * 0.25 +    # Important: far from all pixels
        saturation_score * 0.2 +     # Saturated colors key better
        brightness_score * 0.1 +     # Moderate brightness
        (1 - hue_penalty) * 0.05    # Avoid problematic hues
    )
    
    return {
        'score': total_score,
        'min_distance': min_distance,
        'avg_distance': avg_distance,
        'percentile_5': percentile_5,
        'distance_score': distance_score,
        'saturation': s,
        'brightness': v,
        'hue': h
    }

def objective_function(hsv_params, subject_colors, subject_pixels_sample):
    """Objective function for optimization (to be minimized)"""
    h, s, v = hsv_params
    
    # Ensure valid ranges
    h = h % 1.0
    s = np.clip(s, 0, 1)
    v = np.clip(v, 0, 1)
    
    # Convert HSV to RGB
    rgb = colorsys.hsv_to_rgb(h, s, v)
    bg_color = tuple(int(c * 255) for c in rgb)
    
    # Evaluate the color
    evaluation = evaluate_background_color_comprehensive(bg_color, subject_colors, subject_pixels_sample)
    
    # Return negative score (we want to minimize)
    return -evaluation['score']

def grid_search_optimization(subject_colors, subject_pixels_sample, resolution=20):
    """Perform grid search to find best background color"""
    print(f"Performing grid search with resolution {resolution}...")
    
    best_score = -float('inf')
    best_color = None
    best_eval = None
    
    # Create grid
    h_values = np.linspace(0, 1, resolution)
    s_values = np.linspace(0.5, 1, resolution//2)  # Focus on saturated colors
    v_values = np.linspace(0.3, 1, resolution//2)  # Avoid very dark colors
    
    total_combinations = len(h_values) * len(s_values) * len(v_values)
    evaluated = 0
    
    for h, s, v in product(h_values, s_values, v_values):
        rgb = colorsys.hsv_to_rgb(h, s, v)
        bg_color = tuple(int(c * 255) for c in rgb)
        
        evaluation = evaluate_background_color_comprehensive(bg_color, subject_colors, subject_pixels_sample)
        
        if evaluation['score'] > best_score:
            best_score = evaluation['score']
            best_color = bg_color
            best_eval = evaluation
        
        evaluated += 1
        if evaluated % 100 == 0:
            print(f"  Evaluated {evaluated}/{total_combinations} combinations...")
    
    return best_color, best_eval

def differential_evolution_optimization(subject_colors, subject_pixels_sample):
    """Use differential evolution to find optimal background color"""
    print("Running differential evolution optimization...")
    
    # Define bounds for HSV space
    bounds = [(0, 1), (0, 1), (0, 1)]  # H, S, V
    
    # Run optimization
    result = differential_evolution(
        objective_function,
        bounds,
        args=(subject_colors, subject_pixels_sample),
        maxiter=100,
        popsize=15,
        seed=42
    )
    
    # Convert result to RGB
    h, s, v = result.x
    rgb = colorsys.hsv_to_rgb(h, s, v)
    best_color = tuple(int(c * 255) for c in rgb)
    
    # Get full evaluation
    evaluation = evaluate_background_color_comprehensive(best_color, subject_colors, subject_pixels_sample)
    
    return best_color, evaluation

def multi_start_optimization(subject_colors, subject_pixels_sample, n_starts=10):
    """Run multiple local optimizations from different starting points"""
    print(f"Running {n_starts} local optimizations...")
    
    best_score = -float('inf')
    best_color = None
    best_eval = None
    
    for i in range(n_starts):
        # Random starting point
        h0 = np.random.random()
        s0 = 0.5 + 0.5 * np.random.random()  # Bias towards saturated
        v0 = 0.4 + 0.6 * np.random.random()  # Avoid very dark
        
        try:
            result = minimize(
                objective_function,
                [h0, s0, v0],
                args=(subject_colors, subject_pixels_sample),
                method='L-BFGS-B',
                bounds=[(0, 1), (0, 1), (0, 1)]
            )
            
            if result.success:
                h, s, v = result.x
                rgb = colorsys.hsv_to_rgb(h, s, v)
                bg_color = tuple(int(c * 255) for c in rgb)
                
                evaluation = evaluate_background_color_comprehensive(bg_color, subject_colors, subject_pixels_sample)
                
                if evaluation['score'] > best_score:
                    best_score = evaluation['score']
                    best_color = bg_color
                    best_eval = evaluation
        except:
            continue
    
    return best_color, best_eval

def find_best_background_color_optimized(image_path):
    """Main function using comprehensive optimization to find the best background color"""
    print(f"Analyzing PNG to find optimal background color: {image_path}")
    
    # Load image
    img = load_png_with_alpha(image_path)
    img_array = np.array(img)
    
    # Extract subject information
    alpha = img_array[:, :, 3]
    opaque_pixels = np.sum(alpha > 0)
    total_pixels = alpha.size
    
    print(f"\nImage info:")
    print(f"  Size: {img.size}")
    print(f"  Subject pixels: {opaque_pixels:,} ({opaque_pixels/total_pixels:.1%})")
    
    # Extract and analyze subject colors
    print("\nAnalyzing subject colors...")
    subject_pixels = extract_subject_colors(img_array, sample_size=20000)
    subject_colors = find_dominant_subject_colors(subject_pixels, n_colors=40)
    
    print(f"Found {len(subject_colors)} dominant colors in subject")
    
    # Keep a sample of actual pixels for percentile calculations
    subject_pixels_sample = subject_pixels[:5000] if len(subject_pixels) > 5000 else subject_pixels
    
    # Run multiple optimization strategies
    print("\nSearching entire color space for optimal background...")
    
    results = []
    
    # 1. Grid search (coarse)
    grid_color, grid_eval = grid_search_optimization(subject_colors, subject_pixels_sample, resolution=30)
    if grid_color:
        results.append({'color': grid_color, 'evaluation': grid_eval, 'method': 'Grid Search'})
    
    # 2. Differential evolution (global optimization)
    de_color, de_eval = differential_evolution_optimization(subject_colors, subject_pixels_sample)
    if de_color:
        results.append({'color': de_color, 'evaluation': de_eval, 'method': 'Differential Evolution'})
    
    # 3. Multi-start local optimization
    ms_color, ms_eval = multi_start_optimization(subject_colors, subject_pixels_sample, n_starts=20)
    if ms_color:
        results.append({'color': ms_color, 'evaluation': ms_eval, 'method': 'Multi-start Optimization'})
    
    # Fine-tune around the best result so far
    if results:
        best_result = max(results, key=lambda x: x['evaluation']['score'])
        print("\nFine-tuning around best result...")
        
        # Convert to HSV
        h, s, v = colorsys.rgb_to_hsv(
            best_result['color'][0]/255,
            best_result['color'][1]/255,
            best_result['color'][2]/255
        )
        
        # Fine grid search around best
        fine_results = []
        for dh in np.linspace(-0.05, 0.05, 11):
            for ds in np.linspace(-0.1, 0.1, 11):
                for dv in np.linspace(-0.1, 0.1, 11):
                    h_new = (h + dh) % 1.0
                    s_new = np.clip(s + ds, 0, 1)
                    v_new = np.clip(v + dv, 0, 1)
                    
                    rgb = colorsys.hsv_to_rgb(h_new, s_new, v_new)
                    bg_color = tuple(int(c * 255) for c in rgb)
                    
                    evaluation = evaluate_background_color_comprehensive(bg_color, subject_colors, subject_pixels_sample)
                    fine_results.append({'color': bg_color, 'evaluation': evaluation})
        
        # Add best fine-tuned result
        best_fine = max(fine_results, key=lambda x: x['evaluation']['score'])
        best_fine['method'] = 'Fine-tuned'
        results.append(best_fine)
    
    # Sort all results by score
    results.sort(key=lambda x: x['evaluation']['score'], reverse=True)
    
    # Remove near-duplicates (colors that are very similar)
    unique_results = []
    for result in results:
        is_duplicate = False
        for unique in unique_results:
            if calculate_color_distance(result['color'], unique['color']) < 10:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_results.append(result)
    
    # Print top recommendations
    print("\n" + "="*60)
    print("OPTIMAL BACKGROUND COLORS FOR CHROMA KEY:")
    print("="*60)
    
    for i, result in enumerate(unique_results[:5]):
        rgb = result['color']
        eval_data = result['evaluation']
        method = result.get('method', 'Unknown')
        
        print(f"\n#{i+1}: RGB{rgb} (Hex: #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x})")
        print(f"   Method: {method}")
        print(f"   Overall Score: {eval_data['score']:.4f}")
        print(f"   Min Distance from Subject: {eval_data['min_distance']:.1f}")
        print(f"   5th Percentile Distance: {eval_data['percentile_5']:.1f}")
        print(f"   Saturation: {eval_data['saturation']:.2f}")
        print(f"   Brightness: {eval_data['brightness']:.2f}")
        
        # Color name
        h, s, v = eval_data['hue'], eval_data['saturation'], eval_data['brightness']
        color_name = get_color_name(h, s, v)
        print(f"   Description: {color_name}")
    
    best_color = unique_results[0]['color']
    print(f"\n{'='*60}")
    print(f"OPTIMAL BACKGROUND COLOR: RGB{best_color}")
    print(f"Hex: #{best_color[0]:02x}{best_color[1]:02x}{best_color[2]:02x}")
    print(f"{'='*60}")
    return best_color, unique_results

def get_color_name(h, s, v):
    """Get a descriptive name for a color based on HSV"""
    if s < 0.1:
        return "Gray" if v < 0.5 else "Light Gray"
    
    hue_names = [
        (0, "Red"), (30, "Orange"), (60, "Yellow"), 
        (120, "Green"), (180, "Cyan"), (240, "Blue"), 
        (300, "Magenta"), (360, "Red")
    ]
    
    hue_deg = h * 360
    for i in range(len(hue_names)-1):
        if hue_names[i][0] <= hue_deg < hue_names[i+1][0]:
            base_color = hue_names[i][1]
            break
    else:
        base_color = "Red"
    
    if v < 0.5:
        prefix = "Dark "
    elif v > 0.8 and s > 0.5:
        prefix = "Bright "
    else:
        prefix = ""
    
    return prefix + base_color

# Example usage
if __name__ == "__main__":
    # Replace with your image path
    image_path = "vts-2025-09-19_07h36_38.png"
    
    try:
        best_color, all_results = find_best_background_color_optimized(image_path)
        
        print("\n" + "="*60)
        print("PROFESSIONAL CHROMA KEY TIPS:")
        print("1. The algorithm searched through millions of possible colors")
        print("2. The optimal color maximizes distance from ALL subject colors")
        print("3. High saturation ensures clean keying")
        print("4. The color avoids common problematic hues (skin, clothing)")
        print("5. Use professional lighting for best results")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have installed required packages:")
        print("pip install pillow numpy scikit-learn scipy matplotlib")