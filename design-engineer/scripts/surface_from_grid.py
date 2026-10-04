"""Construct a CAD face from an ordered 3D point grid with fixed parameters.

Requires build123d, NumPy and SciPy in the task environment. Points must be
ordered by two surface directions; this does not reconstruct unordered meshes.
The returned face still needs envelope, trimming, joining and solid checks.
"""
import numpy as np
from scipy.interpolate import RectBivariateSpline
from build123d import Face
from OCP.Geom import Geom_BSplineSurface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pnt

try:  # OCCT 8 collection names
    from OCP.collections import Array2_gp_Pnt, Array1_double, Array1_int
except ImportError:  # OCCT 7 collection names
    from OCP.TColgp import TColgp_Array2OfPnt as Array2_gp_Pnt
    from OCP.TColStd import TColStd_Array1OfReal as Array1_double
    from OCP.TColStd import TColStd_Array1OfInteger as Array1_int


def surface_from_grid(points):
    """Interpolate points[u_index][v_index] using a cubic tensor-product spline.

    Uniform parameters follow grid indices, not distances or image brightness.
    The caller must supply an appropriate grid and inspect between samples.
    """
    data = np.asarray(points, dtype=float)
    if data.ndim != 3 or data.shape[2] != 3 or min(data.shape[:2]) < 4:
        raise ValueError('Expected an ordered grid of at least 4 x 4 XYZ points')
    if not np.isfinite(data).all():
        raise ValueError('Grid coordinates must be finite')
    nu, nv, _ = data.shape
    u, v = np.linspace(0, 1, nu), np.linspace(0, 1, nv)
    fits = [RectBivariateSpline(u, v, data[:, :, k], kx=3, ky=3, s=0)
            for k in range(3)]
    tx, ty = fits[0].get_knots()
    coefficients = np.stack([f.get_coeffs().reshape(nu, nv) for f in fits], axis=-1)
    poles = Array2_gp_Pnt(1, nu, 1, nv)
    for i in range(nu):
        for j in range(nv):
            poles.SetValue(i+1, j+1, gp_Pnt(*map(float, coefficients[i, j])))

    def knots(values):
        unique, counts = np.unique(values, return_counts=True)
        k, m = Array1_double(1, len(unique)), Array1_int(1, len(unique))
        for i, (value, count) in enumerate(zip(unique, counts), 1):
            k.SetValue(i, float(value))
            m.SetValue(i, int(count))
        return k, m

    uk, um = knots(tx)
    vk, vm = knots(ty)
    surface = Geom_BSplineSurface(poles, uk, vk, um, vm, 3, 3, False, False)
    face = Face(BRepBuilderAPI_MakeFace(surface, 1e-7).Face())
    if not face.is_valid:
        raise ValueError('Constructed surface is invalid')
    return face
