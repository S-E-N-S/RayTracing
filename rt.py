"""
MIT License
Copyright (c) 2017 Cyrille Rossant
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""



import numpy as np
import matplotlib.pyplot as plt

w = 400
h = 300
MAX_DEPTH_RAY_TRACING = 5  # how many times we can split a single ray
RGB_DIM = 3  # how many components are needed to determine color
NORM_BIAS_SCALE = 0.0001  # displacement for the normal vector 


# List of objects.
color_plane0 = 1.0 * np.ones(RGB_DIM)
color_plane1 = 0.0 * np.ones(RGB_DIM)
scene = [add_sphere([0.75, 0.1, 1.0], 0.6, [0.0, 0.0, 1.0]),
         add_transparent_sphere([-0.75, 0.1, 2.25], 0.6, [0.5, 0.223, 0.5], 0.8),
         add_sphere([-2.75, 0.1, 3.5], 0.6, [1.0, 0.572, 0.184]),
         add_plane([0.0, -0.5, 0.0], [0.0, 1.0, 0.0]),
   ]

# Light position and color.
L = np.array([5.0, 5.0, -10.0])
color_light = np.ones(3)

# Default light and material parameters.
ambient = 0.05
diffuse_c = 1.0
specular_c = 1.0
specular_k = 50

col = np.zeros(3)  # Current color.
O = np.array([0.0, 0.35, -1.0])  # Camera.
Q = np.array([0.0, 0.0, 0.0])  # Camera pointing to.
img = np.zeros((h, w, RGB_DIM))

r = float(w) / h
# Screen coordinates: x0, y0, x1, y1.
S = (-1.0, -1.0 / r + 0.25, 1.0, 1.0 / r + 0.25)


def normalize(x):
    x /= np.linalg.norm(x)
    return x


def intersect_plane(O, D, P, N):
    # Return the distance from O to the intersection of the ray (O, D) with the 
    # plane (P, N), or +inf if there is no intersection.
    # O and P are 3D points, D and N (normal) are normalized vectors.
    denom = np.dot(D, N)
    if np.abs(denom) < 1e-6:
        return np.inf
    d = np.dot(P - O, N) / denom
    if d < 0:
        return np.inf
    return d


def intersect_sphere(O, D, S, R):
    # Return the distance from O to the intersection of the ray (O, D) with the 
    # sphere (S, R), or +inf if there is no intersection.
    # O and S are 3D points, D (direction) is a normalized vector, R is a scalar.
    a = np.dot(D, D)
    OS = O - S
    b = 2 * np.dot(D, OS)
    c = np.dot(OS, OS) - R * R
    disc = b * b - 4 * a * c
    if disc > 0:
        distSqrt = np.sqrt(disc)
        q = (-b - distSqrt) / 2.0 if b < 0 else (-b + distSqrt) / 2.0
        t0 = q / a
        t1 = c / q
        t0, t1 = min(t0, t1), max(t0, t1)
        if t1 >= 0:
            return t1 if t0 < 0 else t0
    return np.inf


def intersect(O, D, obj):
    if obj['type'] == 'plane':
        return intersect_plane(O, D, obj['position'], obj['normal'])
    elif obj['type'] == 'sphere':
        return intersect_sphere(O, D, obj['position'], obj['radius'])


def get_normal(obj, M):
    # Find normal.
    if obj['type'] == 'sphere':
        N = normalize(M - obj['position'])
    elif obj['type'] == 'plane':
        N = obj['normal']
    return N


def get_color(obj, M):
    color = obj['color']
    if not hasattr(color, '__len__'):
        color = color(M)
    return color


def get_refraction(obj):
    return obj['refraction'] if 'refraction' in obj.keys() else None


def trace_ray(rayO, rayD):
    """
    trace_ray takes rays and looks for an intersection with objects on the scene
    """
    # Find first point of intersection with the scene.
    t = np.inf
    for i, obj in enumerate(scene):
        t_obj = intersect(rayO, rayD, obj)
        if t_obj < t:
            t, obj_idx = t_obj, i
    # Return None if the ray does not intersect any object.
    if t == np.inf:
        return
    # Find the object.
    obj = scene[obj_idx]
    # Find the point of intersection on the object.
    M = rayO + rayD * t
    # Find properties of the object.
    N = get_normal(obj, M)
    color = get_color(obj, M)
    toL = normalize(L - M)
    toO = normalize(O - M)
    # Shadow: find if the point is shadowed or not.
    l = [intersect(M + N * NORM_BIAS_SCALE, toL, obj_sh) 
            for k, obj_sh in enumerate(scene) if k != obj_idx]
    if l and min(l) < np.inf:
        return
    # Start computing the color.
    col_ray = ambient
    # Lambert shading (diffuse).
    col_ray += obj.get('diffuse_c', diffuse_c) * max(np.dot(N, toL), 0) * color
    # Blinn-Phong shading (specular).
    col_ray += obj.get('specular_c', specular_c) * max(np.dot(N, normalize(toL + toO)), 0) ** specular_k * color_light
    return obj, M, N, col_ray


def add_sphere(position, radius, color):
    return dict(type='sphere', position=np.array(position), 
        radius=np.array(radius), color=np.array(color), reflection=.5, refraction=None)


def add_transparent_sphere(position, radius, color, refraction):
    return dict(type='sphere', position=np.array(position),
        radius=np.array(radius), color=np.array(color), reflection=.5, refraction=refraction)


def add_plane(position, normal):
    return dict(type='plane', position=np.array(position), 
        normal=np.array(normal),
        color=lambda M: (color_plane0 
            if (int(M[0] * 2) % 2) == (int(M[2] * 2) % 2) else color_plane1),
        diffuse_c=0.75, specular_c=0.5, reflection=0.25)


def find_refracted(N, M, rayO, rayD, refraction):
    # ray goes in/out object
    N *= 1 if np.dot(rayD, N) <= 0 else -1
    rayO_refracted = M - N * NORM_BIAS_SCALE
    # find sin (sin^2 + cos^2 = 1)
    # cos is dot product
    fall_sin = (1 - np.dot(rayD, N) ** 2) ** 0.5
    refraction_sin = fall_sin * refraction
    refraction_cos = (1 - refraction_sin ** 2) ** 0.5
    refraction_cot = refraction_cos / refraction_sin
    surf_dir = N * np.dot(rayD, N) + rayD
    rayD_refracted = normalize(N + surf_dir * refraction_cot)
    return rayO_refracted, rayD_refracted


def cast_ray(rayO, rayD, reflection, depth=0):
    """
    cast_ray takes ray, get trace_ray result (finds an intersection with objects in the scene)
    and cast another rays from an intersection point recursively (then finds sum to get the final color)
    """
    ray_sum = np.zeros(RGB_DIM)
    if depth > MAX_DEPTH_RAY_TRACING:
        return ray_sum
    traced = trace_ray(rayO, rayD)
    if not traced:
        return ray_sum
    obj, M, N, col_ray = traced
    # Reflection: create a new ray.
    rayO, rayD = M + N * NORM_BIAS_SCALE, normalize(rayD - 2 * np.dot(rayD, N) * N)
    refraction = get_refraction(obj)
    if refraction is not None:
        # find refracted rays
        rayO_refracted, rayD_refracted = find_refracted(N, M, rayO, rayD, refraction)
        # add rays casted recursively
        ray_sum += cast_ray(rayO_refracted, rayD_refracted, reflection, depth + 1)
    # rayO -- new point with ray
    # rayD -- new ray direction
    # col += reflection * col_ray
    reflection *= obj.get('reflection', 1.0)
    ray_sum += cast_ray(rayO, rayD, reflection, depth + 1)
    return ray_sum + reflection * col_ray

# Loop through all pixels.
for i, x in enumerate(np.linspace(S[0], S[2], w)):
    if i % 10 == 0:
        print(i / float(w) * 100, "%")
    for j, y in enumerate(np.linspace(S[1], S[3], h)):
        #print(f"{j, y}")
        col[:] = 0
        Q[:2] = (x, y)
        D = normalize(Q - O)
        rayO, rayD = O, D
        reflection = 1.
        # Loop through initial and secondary rays.
        col = cast_ray(rayO, rayD, reflection)
        img[h - j - 1, i, :] = np.clip(col, 0, 1)

# save the result
plt.imsave('fig.png', img)
