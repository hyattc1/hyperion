# Origin: red-team drill 4 (docs/drills/redteam/redteam-4.md). Built blind in 41 minutes by a rival team given no
# design philosophy ("the strongest team in the room, build whatever scores most"), against the same brief and kit
# interface as rivals 1 to 3, with no access to this repository or to any earlier rival; frozen at md5
# 28a0655f583ce9f5d6ac11b72bed0d72 and copied here unchanged apart from this header. The archived original is
# docs/drills/redteam/rival4_bot.py. It is played through hyperion.sim.bestiary.Rival4Bot (registry name `rival4`).
# It is the judge: no candidate core is measured against it or tuned on it before the one final comparison.
# Do not edit; a new rival is a new file.
"""rival_bot: ICM-driven push/fold + positional preflop + rule-based postflop + per-seat opponent model.
Stdlib only. No Monte Carlo at decision time; preflop equities are an offline MC table embedded below."""
import random as _random
try:
    from kit import Agent as _Agent
except Exception:  # pragma: no cover
    class _Agent(object):
        def new_table(self, rules, seat, n_players): pass
        def act(self, obs): raise NotImplementedError
        def hand_end(self, result): pass

_X = [0.03, 0.06, 0.1, 0.15, 0.2, 0.3, 0.45, 0.65, 1.0]
_VR = {'12,12,0': 0.8454, '12,11,1': 0.6708, '12,11,0': 0.6548, '12,10,1': 0.6572, '12,10,0': 0.6526, '12,9,1': 0.651, '12,9,0': 0.6272, '12,8,1': 0.647, '12,8,0': 0.6316, '12,7,1': 0.626, '12,7,0': 0.6154, '12,6,1': 0.618, '12,6,0': 0.5878, '12,5,1': 0.6016, '12,5,0': 0.5692, '12,4,1': 0.577, '12,4,0': 0.5754, '12,3,1': 0.5922, '12,3,0': 0.5622, '12,2,1': 0.59, '12,2,0': 0.5596, '12,1,1': 0.5904, '12,1,0': 0.5396, '12,0,1': 0.5824, '12,0,0': 0.5366, '11,11,0': 0.8326, '11,10,1': 0.6414, '11,10,0': 0.6244, '11,9,1': 0.63, '11,9,0': 0.6104, '11,8,1': 0.6226, '11,8,0': 0.6052, '11,7,1': 0.606, '11,7,0': 0.586, '11,6,1': 0.576, '11,6,0': 0.5688, '11,5,1': 0.572, '11,5,0': 0.5566, '11,4,1': 0.562, '11,4,0': 0.53, '11,3,1': 0.5612, '11,3,0': 0.5206, '11,2,1': 0.5434, '11,2,0': 0.5178, '11,1,1': 0.5478, '11,1,0': 0.5172, '11,0,1': 0.517, '11,0,0': 0.5018, '10,10,0': 0.7996, '10,9,1': 0.6096, '10,9,0': 0.575, '10,8,1': 0.601, '10,8,0': 0.5792, '10,7,1': 0.5642, '10,7,0': 0.5628, '10,6,1': 0.556, '10,6,0': 0.5484, '10,5,1': 0.5156, '10,5,0': 0.5174, '10,4,1': 0.5428, '10,4,0': 0.5106, '10,3,1': 0.5128, '10,3,0': 0.4938, '10,2,1': 0.5006, '10,2,0': 0.4838, '10,1,1': 0.5114, '10,1,0': 0.4874, '10,0,1': 0.4892, '10,0,0': 0.4728, '9,9,0': 0.7714, '9,8,1': 0.565, '9,8,0': 0.5628, '9,7,1': 0.556, '9,7,0': 0.5384, '9,6,1': 0.5454, '9,6,0': 0.5102, '9,5,1': 0.5382, '9,5,0': 0.5, '9,4,1': 0.4966, '9,4,0': 0.4878, '9,3,1': 0.5182, '9,3,0': 0.4594, '9,2,1': 0.4746, '9,2,0': 0.4502, '9,1,1': 0.4898, '9,1,0': 0.4482, '9,0,1': 0.4746, '9,0,0': 0.445, '8,8,0': 0.7538, '8,7,1': 0.5378, '8,7,0': 0.4954, '8,6,1': 0.516, '8,6,0': 0.497, '8,5,1': 0.5114, '8,5,0': 0.4834, '8,4,1': 0.492, '8,4,0': 0.4714, '8,3,1': 0.4714, '8,3,0': 0.4272, '8,2,1': 0.4738, '8,2,0': 0.4312, '8,1,1': 0.4582, '8,1,0': 0.4236, '8,0,1': 0.4498, '8,0,0': 0.4356, '7,7,0': 0.7304, '7,6,1': 0.5028, '7,6,0': 0.4584, '7,5,1': 0.5032, '7,5,0': 0.4766, '7,4,1': 0.4808, '7,4,0': 0.4628, '7,3,1': 0.4448, '7,3,0': 0.4218, '7,2,1': 0.4266, '7,2,0': 0.4146, '7,1,1': 0.4288, '7,1,0': 0.3996, '7,0,1': 0.4068, '7,0,0': 0.4018, '6,6,0': 0.6994, '6,5,1': 0.4762, '6,5,0': 0.4534, '6,4,1': 0.4664, '6,4,0': 0.4322, '6,3,1': 0.448, '6,3,0': 0.417, '6,2,1': 0.4208, '6,2,0': 0.3892, '6,1,1': 0.4104, '6,1,0': 0.3768, '6,0,1': 0.4216, '6,0,0': 0.3662, '5,5,0': 0.663, '5,4,1': 0.455, '5,4,0': 0.4188, '5,3,1': 0.4378, '5,3,0': 0.4116, '5,2,1': 0.4256, '5,2,0': 0.4036, '5,1,1': 0.3846, '5,1,0': 0.3634, '5,0,1': 0.3694, '5,0,0': 0.354, '4,4,0': 0.6202, '4,3,1': 0.438, '4,3,0': 0.4018, '4,2,1': 0.4222, '4,2,0': 0.3764, '4,1,1': 0.395, '4,1,0': 0.3678, '4,0,1': 0.3874, '4,0,0': 0.3282, '3,3,0': 0.6022, '3,2,1': 0.408, '3,2,0': 0.373, '3,1,1': 0.3808, '3,1,0': 0.378, '3,0,1': 0.3884, '3,0,0': 0.33, '2,2,0': 0.579, '2,1,1': 0.3878, '2,1,0': 0.3472, '2,0,1': 0.3772, '2,0,0': 0.3538, '1,1,0': 0.5406, '1,0,1': 0.3458, '1,0,0': 0.329, '0,0,0': 0.5178}
_PCT = {'12,12,0': 0.0045, '12,11,1': 0.0347, '12,11,0': 0.0513, '12,10,1': 0.0422, '12,10,0': 0.0603, '12,9,1': 0.0633, '12,9,0': 0.0905, '12,8,1': 0.0664, '12,8,0': 0.0784, '12,7,1': 0.0935, '12,7,0': 0.1222, '12,6,1': 0.1131, '12,6,0': 0.175, '12,5,1': 0.1538, '12,5,0': 0.2368, '12,4,1': 0.2036, '12,4,0': 0.2157, '12,3,1': 0.1599, '12,3,0': 0.279, '12,2,1': 0.1659, '12,2,0': 0.2941, '12,1,1': 0.1629, '12,1,0': 0.3439, '12,0,1': 0.187, '12,0,0': 0.368, '11,11,0': 0.009, '11,10,1': 0.0694, '11,10,0': 0.1026, '11,9,1': 0.0814, '11,9,0': 0.1312, '11,8,1': 0.1056, '11,8,0': 0.1463, '11,7,1': 0.1373, '11,7,0': 0.184, '11,6,1': 0.2066, '11,6,0': 0.2459, '11,5,1': 0.2278, '11,5,0': 0.3032, '11,4,1': 0.2821, '11,4,0': 0.3771, '11,3,1': 0.2851, '11,3,0': 0.3861, '11,2,1': 0.3273, '11,2,0': 0.3982, '11,1,1': 0.3213, '11,1,0': 0.4208, '11,0,1': 0.4238, '11,0,0': 0.4721, '10,10,0': 0.0136, '10,9,1': 0.1342, '10,9,0': 0.2247, '10,8,1': 0.1569, '10,8,0': 0.1961, '10,7,1': 0.2519, '10,7,0': 0.2609, '10,6,1': 0.3062, '10,6,0': 0.3183, '10,5,1': 0.4299, '10,5,0': 0.4118, '10,4,1': 0.3303, '10,4,0': 0.448, '10,3,1': 0.4329, '10,3,0': 0.5143, '10,2,1': 0.4751, '10,2,0': 0.5505, '10,1,1': 0.4359, '10,1,0': 0.5415, '10,0,1': 0.5234, '10,0,0': 0.5928, '9,9,0': 0.0181, '9,8,1': 0.2489, '9,8,0': 0.27, '9,7,1': 0.3092, '9,7,0': 0.3529, '9,6,1': 0.3243, '9,6,0': 0.457, '9,5,1': 0.356, '9,5,0': 0.4842, '9,4,1': 0.4962, '9,4,0': 0.5324, '9,3,1': 0.3891, '9,3,0': 0.6259, '9,2,1': 0.5777, '9,2,0': 0.6591, '9,1,1': 0.5204, '9,1,0': 0.6712, '9,0,1': 0.5807, '9,0,0': 0.6833, '8,8,0': 0.0226, '8,7,1': 0.359, '8,7,0': 0.5053, '8,6,1': 0.4268, '8,6,0': 0.4932, '8,5,1': 0.4389, '8,5,0': 0.5596, '8,4,1': 0.5173, '8,4,0': 0.6018, '8,3,1': 0.6048, '8,3,0': 0.7315, '8,2,1': 0.5837, '8,2,0': 0.7195, '8,1,1': 0.638, '8,1,0': 0.7466, '8,0,1': 0.6621, '8,0,0': 0.7014, '7,7,0': 0.0271, '7,6,1': 0.463, '7,6,0': 0.635, '7,5,1': 0.46, '7,5,0': 0.5716, '7,4,1': 0.5626, '7,4,0': 0.6169, '7,3,1': 0.6863, '7,3,0': 0.7587, '7,2,1': 0.7345, '7,2,0': 0.7919, '7,1,1': 0.7225, '7,1,0': 0.8462, '7,0,1': 0.81, '7,0,0': 0.8281, '6,6,0': 0.0317, '6,5,1': 0.5747, '6,5,0': 0.6501, '6,4,1': 0.6078, '6,4,0': 0.7104, '6,3,1': 0.6742, '6,3,0': 0.7828, '6,2,1': 0.7647, '6,2,0': 0.8582, '6,1,1': 0.8039, '6,1,0': 0.8944, '6,0,1': 0.7617, '6,0,0': 0.9336, '5,5,0': 0.0392, '5,4,1': 0.641, '5,4,0': 0.7738, '5,3,1': 0.6923, '5,3,0': 0.8009, '5,2,1': 0.7376, '5,2,0': 0.819, '5,1,1': 0.8703, '5,1,0': 0.9427, '5,0,1': 0.9155, '5,0,0': 0.9517, '4,4,0': 0.1101, '4,3,1': 0.6893, '4,3,0': 0.8371, '4,2,1': 0.7496, '4,2,0': 0.9035, '4,1,1': 0.8492, '4,1,0': 0.9246, '4,0,1': 0.8673, '4,0,0': 1.0, '3,3,0': 0.1508, '3,2,1': 0.8069, '3,2,0': 0.9125, '3,1,1': 0.8733, '3,1,0': 0.8824, '3,0,1': 0.8612, '3,0,0': 0.9819, '2,2,0': 0.2006, '2,1,1': 0.8643, '2,1,0': 0.9698, '2,0,1': 0.8854, '2,0,0': 0.9608, '1,1,0': 0.3348, '1,0,1': 0.9729, '1,0,0': 0.991, '0,0,0': 0.4027}
_VX = {'12,12,0': [0.79, 0.809, 0.853, 0.855, 0.867, 0.855, 0.868, 0.856, 0.864], '12,11,1': [0.406, 0.452, 0.567, 0.616, 0.611, 0.667, 0.664, 0.676, 0.689], '12,11,0': [0.347, 0.439, 0.578, 0.625, 0.659, 0.636, 0.653, 0.659, 0.665], '12,10,1': [0.382, 0.374, 0.531, 0.567, 0.595, 0.648, 0.656, 0.655, 0.636], '12,10,0': [0.329, 0.32, 0.463, 0.558, 0.59, 0.651, 0.613, 0.609, 0.644], '12,9,1': [0.344, 0.364, 0.432, 0.518, 0.56, 0.595, 0.606, 0.642, 0.626], '12,9,0': [0.301, 0.326, 0.424, 0.48, 0.534, 0.591, 0.607, 0.626, 0.623], '12,8,1': [0.29, 0.315, 0.373, 0.498, 0.581, 0.591, 0.621, 0.665, 0.646], '12,8,0': [0.283, 0.288, 0.372, 0.437, 0.517, 0.541, 0.578, 0.629, 0.58], '12,7,1': [0.326, 0.301, 0.331, 0.427, 0.496, 0.534, 0.595, 0.593, 0.624], '12,7,0': [0.237, 0.272, 0.306, 0.36, 0.469, 0.499, 0.557, 0.57, 0.603], '12,6,1': [0.281, 0.317, 0.333, 0.417, 0.439, 0.5, 0.522, 0.562, 0.608], '12,6,0': [0.221, 0.246, 0.311, 0.349, 0.448, 0.499, 0.528, 0.539, 0.572], '12,5,1': [0.294, 0.281, 0.324, 0.411, 0.438, 0.447, 0.558, 0.626, 0.616], '12,5,0': [0.281, 0.253, 0.298, 0.36, 0.408, 0.453, 0.537, 0.548, 0.615], '12,4,1': [0.274, 0.324, 0.317, 0.386, 0.415, 0.474, 0.506, 0.552, 0.571], '12,4,0': [0.219, 0.253, 0.274, 0.375, 0.372, 0.449, 0.519, 0.522, 0.566], '12,3,1': [0.287, 0.309, 0.32, 0.386, 0.429, 0.452, 0.497, 0.547, 0.625], '12,3,0': [0.253, 0.234, 0.254, 0.354, 0.376, 0.484, 0.492, 0.52, 0.593], '12,2,1': [0.301, 0.3, 0.323, 0.401, 0.423, 0.457, 0.504, 0.543, 0.608], '12,2,0': [0.281, 0.28, 0.274, 0.4, 0.42, 0.411, 0.496, 0.51, 0.527], '12,1,1': [0.303, 0.308, 0.278, 0.407, 0.445, 0.483, 0.506, 0.507, 0.566], '12,1,0': [0.247, 0.235, 0.287, 0.344, 0.402, 0.402, 0.477, 0.522, 0.538], '12,0,1': [0.281, 0.293, 0.318, 0.415, 0.417, 0.425, 0.522, 0.51, 0.601], '12,0,0': [0.252, 0.284, 0.287, 0.341, 0.373, 0.421, 0.469, 0.477, 0.561], '11,11,0': [0.659, 0.697, 0.675, 0.784, 0.76, 0.752, 0.822, 0.812, 0.839], '11,10,1': [0.299, 0.352, 0.39, 0.471, 0.557, 0.505, 0.596, 0.636, 0.669], '11,10,0': [0.32, 0.322, 0.335, 0.423, 0.5, 0.55, 0.546, 0.552, 0.61], '11,9,1': [0.333, 0.389, 0.35, 0.419, 0.448, 0.497, 0.559, 0.608, 0.627], '11,9,0': [0.281, 0.316, 0.324, 0.371, 0.456, 0.468, 0.513, 0.581, 0.604], '11,8,1': [0.27, 0.327, 0.35, 0.403, 0.397, 0.498, 0.544, 0.607, 0.603], '11,8,0': [0.271, 0.289, 0.338, 0.343, 0.396, 0.458, 0.462, 0.566, 0.61], '11,7,1': [0.256, 0.334, 0.333, 0.37, 0.404, 0.441, 0.496, 0.549, 0.591], '11,7,0': [0.224, 0.271, 0.296, 0.33, 0.345, 0.368, 0.483, 0.555, 0.563], '11,6,1': [0.239, 0.258, 0.323, 0.337, 0.374, 0.406, 0.473, 0.545, 0.578], '11,6,0': [0.205, 0.254, 0.307, 0.277, 0.355, 0.329, 0.454, 0.506, 0.534], '11,5,1': [0.243, 0.271, 0.327, 0.323, 0.368, 0.364, 0.464, 0.485, 0.56], '11,5,0': [0.207, 0.212, 0.323, 0.334, 0.317, 0.354, 0.469, 0.488, 0.528], '11,4,1': [0.264, 0.324, 0.327, 0.313, 0.355, 0.41, 0.427, 0.563, 0.562], '11,4,0': [0.21, 0.226, 0.258, 0.319, 0.307, 0.398, 0.439, 0.483, 0.571], '11,3,1': [0.255, 0.267, 0.283, 0.33, 0.333, 0.401, 0.473, 0.513, 0.557], '11,3,0': [0.205, 0.259, 0.275, 0.307, 0.38, 0.33, 0.374, 0.49, 0.583], '11,2,1': [0.225, 0.258, 0.298, 0.31, 0.356, 0.327, 0.407, 0.483, 0.531], '11,2,0': [0.226, 0.217, 0.295, 0.293, 0.324, 0.338, 0.437, 0.43, 0.529], '11,1,1': [0.261, 0.248, 0.311, 0.313, 0.338, 0.358, 0.439, 0.509, 0.526], '11,1,0': [0.215, 0.242, 0.284, 0.295, 0.329, 0.316, 0.43, 0.443, 0.49], '11,0,1': [0.239, 0.284, 0.331, 0.319, 0.344, 0.381, 0.435, 0.45, 0.539], '11,0,0': [0.223, 0.245, 0.308, 0.289, 0.308, 0.344, 0.371, 0.447, 0.522], '10,10,0': [0.503, 0.623, 0.663, 0.669, 0.698, 0.723, 0.719, 0.76, 0.792], '10,9,1': [0.317, 0.348, 0.33, 0.414, 0.384, 0.44, 0.527, 0.558, 0.601], '10,9,0': [0.275, 0.334, 0.335, 0.335, 0.362, 0.424, 0.446, 0.529, 0.596], '10,8,1': [0.298, 0.338, 0.351, 0.343, 0.397, 0.453, 0.483, 0.569, 0.56], '10,8,0': [0.267, 0.316, 0.324, 0.357, 0.37, 0.41, 0.45, 0.484, 0.56], '10,7,1': [0.252, 0.31, 0.36, 0.334, 0.376, 0.411, 0.417, 0.486, 0.578], '10,7,0': [0.236, 0.27, 0.302, 0.303, 0.345, 0.381, 0.415, 0.518, 0.56], '10,6,1': [0.239, 0.296, 0.307, 0.331, 0.396, 0.385, 0.426, 0.507, 0.558], '10,6,0': [0.186, 0.262, 0.293, 0.307, 0.299, 0.303, 0.353, 0.489, 0.566], '10,5,1': [0.233, 0.263, 0.294, 0.331, 0.353, 0.385, 0.4, 0.462, 0.603], '10,5,0': [0.177, 0.236, 0.291, 0.28, 0.304, 0.322, 0.359, 0.427, 0.545], '10,4,1': [0.226, 0.273, 0.327, 0.327, 0.362, 0.37, 0.431, 0.421, 0.546], '10,4,0': [0.214, 0.254, 0.29, 0.272, 0.307, 0.335, 0.318, 0.441, 0.47], '10,3,1': [0.207, 0.303, 0.317, 0.289, 0.328, 0.384, 0.41, 0.421, 0.545], '10,3,0': [0.184, 0.241, 0.243, 0.256, 0.322, 0.303, 0.353, 0.448, 0.507], '10,2,1': [0.236, 0.311, 0.287, 0.34, 0.344, 0.332, 0.37, 0.44, 0.526], '10,2,0': [0.169, 0.277, 0.255, 0.255, 0.276, 0.306, 0.394, 0.387, 0.472], '10,1,1': [0.225, 0.279, 0.309, 0.338, 0.351, 0.369, 0.371, 0.452, 0.501], '10,1,0': [0.176, 0.218, 0.301, 0.265, 0.267, 0.327, 0.317, 0.418, 0.497], '10,0,1': [0.241, 0.273, 0.281, 0.319, 0.355, 0.403, 0.376, 0.42, 0.46], '10,0,0': [0.195, 0.234, 0.305, 0.248, 0.286, 0.308, 0.34, 0.406, 0.431], '9,9,0': [0.44, 0.519, 0.617, 0.583, 0.665, 0.684, 0.673, 0.762, 0.761], '9,8,1': [0.256, 0.363, 0.368, 0.346, 0.401, 0.403, 0.443, 0.534, 0.562], '9,8,0': [0.204, 0.319, 0.371, 0.347, 0.328, 0.385, 0.437, 0.506, 0.537], '9,7,1': [0.244, 0.331, 0.331, 0.327, 0.353, 0.427, 0.435, 0.52, 0.551], '9,7,0': [0.201, 0.262, 0.309, 0.329, 0.313, 0.371, 0.371, 0.448, 0.549], '9,6,1': [0.271, 0.337, 0.304, 0.365, 0.343, 0.361, 0.424, 0.453, 0.507], '9,6,0': [0.183, 0.263, 0.323, 0.299, 0.267, 0.345, 0.36, 0.465, 0.506], '9,5,1': [0.258, 0.29, 0.266, 0.305, 0.349, 0.374, 0.382, 0.425, 0.536], '9,5,0': [0.184, 0.238, 0.307, 0.256, 0.296, 0.277, 0.372, 0.383, 0.507], '9,4,1': [0.186, 0.271, 0.305, 0.31, 0.34, 0.36, 0.392, 0.479, 0.521], '9,4,0': [0.18, 0.214, 0.279, 0.303, 0.288, 0.283, 0.324, 0.395, 0.509], '9,3,1': [0.194, 0.307, 0.348, 0.336, 0.339, 0.331, 0.385, 0.41, 0.509], '9,3,0': [0.179, 0.257, 0.261, 0.289, 0.3, 0.312, 0.385, 0.386, 0.453], '9,2,1': [0.234, 0.296, 0.266, 0.355, 0.34, 0.326, 0.395, 0.393, 0.426], '9,2,0': [0.152, 0.25, 0.246, 0.26, 0.245, 0.297, 0.369, 0.375, 0.445], '9,1,1': [0.243, 0.263, 0.318, 0.334, 0.333, 0.37, 0.342, 0.391, 0.493], '9,1,0': [0.152, 0.268, 0.272, 0.268, 0.265, 0.306, 0.326, 0.36, 0.491], '9,0,1': [0.201, 0.297, 0.301, 0.353, 0.335, 0.352, 0.306, 0.381, 0.5], '9,0,0': [0.169, 0.252, 0.25, 0.266, 0.321, 0.304, 0.324, 0.319, 0.427], '8,8,0': [0.347, 0.49, 0.523, 0.545, 0.617, 0.659, 0.678, 0.667, 0.76], '8,7,1': [0.235, 0.324, 0.36, 0.348, 0.357, 0.4, 0.407, 0.454, 0.543], '8,7,0': [0.176, 0.316, 0.33, 0.392, 0.324, 0.328, 0.389, 0.433, 0.512], '8,6,1': [0.249, 0.288, 0.331, 0.357, 0.378, 0.332, 0.356, 0.415, 0.511], '8,6,0': [0.135, 0.251, 0.295, 0.307, 0.32, 0.358, 0.353, 0.414, 0.495], '8,5,1': [0.202, 0.268, 0.323, 0.328, 0.321, 0.331, 0.369, 0.429, 0.498], '8,5,0': [0.143, 0.254, 0.339, 0.315, 0.304, 0.324, 0.357, 0.348, 0.493], '8,4,1': [0.195, 0.256, 0.305, 0.32, 0.322, 0.326, 0.324, 0.395, 0.498], '8,4,0': [0.169, 0.244, 0.325, 0.298, 0.311, 0.289, 0.333, 0.343, 0.534], '8,3,1': [0.181, 0.289, 0.272, 0.328, 0.321, 0.354, 0.366, 0.393, 0.457], '8,3,0': [0.14, 0.237, 0.284, 0.277, 0.291, 0.306, 0.348, 0.347, 0.407], '8,2,1': [0.186, 0.292, 0.297, 0.325, 0.33, 0.299, 0.351, 0.372, 0.475], '8,2,0': [0.133, 0.223, 0.251, 0.262, 0.231, 0.285, 0.328, 0.346, 0.407], '8,1,1': [0.164, 0.269, 0.289, 0.31, 0.296, 0.332, 0.33, 0.382, 0.486], '8,1,0': [0.143, 0.2, 0.269, 0.245, 0.256, 0.324, 0.32, 0.315, 0.434], '8,0,1': [0.183, 0.239, 0.308, 0.344, 0.344, 0.301, 0.323, 0.342, 0.453], '8,0,0': [0.138, 0.209, 0.249, 0.242, 0.268, 0.295, 0.301, 0.295, 0.399], '7,7,0': [0.263, 0.407, 0.447, 0.533, 0.584, 0.607, 0.619, 0.659, 0.716], '7,6,1': [0.193, 0.304, 0.38, 0.341, 0.385, 0.389, 0.406, 0.422, 0.489], '7,6,0': [0.173, 0.263, 0.329, 0.305, 0.31, 0.348, 0.334, 0.4, 0.489], '7,5,1': [0.195, 0.289, 0.316, 0.333, 0.397, 0.392, 0.367, 0.387, 0.48], '7,5,0': [0.148, 0.24, 0.286, 0.265, 0.348, 0.368, 0.381, 0.372, 0.402], '7,4,1': [0.186, 0.292, 0.327, 0.321, 0.36, 0.362, 0.375, 0.387, 0.503], '7,4,0': [0.141, 0.238, 0.274, 0.31, 0.311, 0.339, 0.325, 0.333, 0.464], '7,3,1': [0.176, 0.236, 0.324, 0.309, 0.336, 0.326, 0.367, 0.381, 0.463], '7,3,0': [0.133, 0.204, 0.272, 0.265, 0.291, 0.297, 0.292, 0.313, 0.383], '7,2,1': [0.151, 0.266, 0.305, 0.292, 0.303, 0.301, 0.329, 0.364, 0.435], '7,2,0': [0.121, 0.18, 0.252, 0.274, 0.262, 0.273, 0.307, 0.329, 0.381], '7,1,1': [0.162, 0.273, 0.267, 0.317, 0.301, 0.295, 0.345, 0.336, 0.436], '7,1,0': [0.101, 0.218, 0.236, 0.282, 0.31, 0.319, 0.336, 0.325, 0.395], '7,0,1': [0.129, 0.237, 0.283, 0.341, 0.299, 0.342, 0.335, 0.379, 0.399], '7,0,0': [0.114, 0.222, 0.251, 0.226, 0.263, 0.297, 0.287, 0.333, 0.376], '6,6,0': [0.191, 0.332, 0.479, 0.514, 0.546, 0.575, 0.589, 0.666, 0.748], '6,5,1': [0.212, 0.294, 0.349, 0.39, 0.382, 0.405, 0.383, 0.4, 0.482], '6,5,0': [0.177, 0.256, 0.268, 0.32, 0.304, 0.347, 0.348, 0.372, 0.429], '6,4,1': [0.219, 0.275, 0.316, 0.35, 0.388, 0.358, 0.391, 0.363, 0.423], '6,4,0': [0.137, 0.243, 0.295, 0.289, 0.329, 0.333, 0.327, 0.381, 0.42], '6,3,1': [0.196, 0.256, 0.306, 0.345, 0.366, 0.369, 0.386, 0.374, 0.458], '6,3,0': [0.153, 0.237, 0.257, 0.286, 0.296, 0.313, 0.35, 0.354, 0.433], '6,2,1': [0.168, 0.208, 0.28, 0.305, 0.295, 0.352, 0.348, 0.346, 0.424], '6,2,0': [0.126, 0.187, 0.261, 0.267, 0.313, 0.308, 0.3, 0.314, 0.399], '6,1,1': [0.158, 0.231, 0.288, 0.339, 0.28, 0.318, 0.362, 0.297, 0.388], '6,1,0': [0.123, 0.218, 0.252, 0.276, 0.28, 0.284, 0.3, 0.289, 0.343], '6,0,1': [0.144, 0.199, 0.3, 0.299, 0.293, 0.305, 0.342, 0.314, 0.4], '6,0,0': [0.126, 0.175, 0.261, 0.266, 0.284, 0.293, 0.261, 0.291, 0.379], '5,5,0': [0.198, 0.301, 0.449, 0.471, 0.521, 0.574, 0.564, 0.612, 0.673], '5,4,1': [0.234, 0.262, 0.355, 0.394, 0.376, 0.427, 0.385, 0.426, 0.458], '5,4,0': [0.212, 0.249, 0.274, 0.311, 0.324, 0.33, 0.357, 0.423, 0.402], '5,3,1': [0.166, 0.244, 0.325, 0.332, 0.351, 0.358, 0.379, 0.389, 0.457], '5,3,0': [0.15, 0.219, 0.281, 0.326, 0.304, 0.335, 0.341, 0.366, 0.411], '5,2,1': [0.206, 0.211, 0.301, 0.321, 0.361, 0.337, 0.349, 0.372, 0.435], '5,2,0': [0.117, 0.193, 0.224, 0.308, 0.32, 0.328, 0.341, 0.327, 0.424], '5,1,1': [0.182, 0.239, 0.286, 0.294, 0.341, 0.325, 0.333, 0.344, 0.422], '5,1,0': [0.157, 0.18, 0.256, 0.296, 0.287, 0.305, 0.311, 0.321, 0.352], '5,0,1': [0.183, 0.232, 0.293, 0.309, 0.295, 0.358, 0.32, 0.364, 0.425], '5,0,0': [0.114, 0.172, 0.238, 0.27, 0.299, 0.28, 0.287, 0.252, 0.299], '4,4,0': [0.196, 0.3, 0.372, 0.43, 0.474, 0.546, 0.54, 0.583, 0.62], '4,3,1': [0.251, 0.254, 0.338, 0.335, 0.358, 0.347, 0.402, 0.406, 0.419], '4,3,0': [0.188, 0.22, 0.29, 0.324, 0.324, 0.326, 0.365, 0.398, 0.407], '4,2,1': [0.206, 0.288, 0.309, 0.356, 0.321, 0.35, 0.35, 0.386, 0.417], '4,2,0': [0.167, 0.193, 0.267, 0.298, 0.332, 0.311, 0.334, 0.321, 0.365], '4,1,1': [0.214, 0.223, 0.308, 0.319, 0.337, 0.364, 0.378, 0.352, 0.406], '4,1,0': [0.152, 0.208, 0.279, 0.263, 0.302, 0.32, 0.296, 0.338, 0.338], '4,0,1': [0.172, 0.244, 0.269, 0.315, 0.353, 0.29, 0.315, 0.342, 0.388], '4,0,0': [0.129, 0.188, 0.245, 0.266, 0.261, 0.282, 0.327, 0.315, 0.322], '3,3,0': [0.182, 0.281, 0.413, 0.421, 0.453, 0.487, 0.555, 0.55, 0.61], '3,2,1': [0.248, 0.271, 0.36, 0.34, 0.362, 0.365, 0.396, 0.37, 0.399], '3,2,0': [0.222, 0.244, 0.328, 0.288, 0.332, 0.337, 0.341, 0.328, 0.392], '3,1,1': [0.209, 0.253, 0.325, 0.347, 0.346, 0.373, 0.332, 0.362, 0.382], '3,1,0': [0.164, 0.237, 0.297, 0.303, 0.298, 0.303, 0.342, 0.332, 0.385], '3,0,1': [0.17, 0.227, 0.284, 0.333, 0.354, 0.356, 0.34, 0.332, 0.389], '3,0,0': [0.158, 0.211, 0.23, 0.284, 0.264, 0.307, 0.31, 0.28, 0.365], '2,2,0': [0.2, 0.291, 0.382, 0.461, 0.47, 0.474, 0.508, 0.529, 0.591], '2,1,1': [0.207, 0.233, 0.336, 0.34, 0.313, 0.349, 0.35, 0.371, 0.412], '2,1,0': [0.162, 0.238, 0.282, 0.29, 0.309, 0.322, 0.321, 0.305, 0.383], '2,0,1': [0.144, 0.235, 0.299, 0.327, 0.315, 0.305, 0.361, 0.383, 0.387], '2,0,0': [0.16, 0.214, 0.272, 0.304, 0.269, 0.267, 0.296, 0.33, 0.37], '1,1,0': [0.172, 0.276, 0.393, 0.44, 0.435, 0.469, 0.525, 0.572, 0.542], '1,0,1': [0.19, 0.231, 0.277, 0.328, 0.33, 0.351, 0.293, 0.335, 0.322], '1,0,0': [0.152, 0.216, 0.266, 0.289, 0.323, 0.282, 0.274, 0.286, 0.332], '0,0,0': [0.174, 0.257, 0.397, 0.425, 0.411, 0.463, 0.456, 0.497, 0.467]}


# ---- table decode: idx = hi*13+lo suited (hi>lo), lo*13+hi offsuit, r*13+r pairs
def _key(hi, lo, s):
    if hi == lo: return hi * 13 + hi
    return hi * 13 + lo if s else lo * 13 + hi
VR = [0.5] * 169; PCT = [0.5] * 169; VX = [[0.5] * len(_X) for _ in range(169)]
for _k, _v in _VR.items():
    _a = [int(t) for t in _k.split(',')]; _i = _key(_a[0], _a[1], _a[2])
    VR[_i] = _v; PCT[_i] = _PCT[_k]; VX[_i] = _VX[_k]
NX = len(_X)

def eq_vs(idx, w):
    """equity of hand idx vs a top-w range (0<w<=1), interpolated."""
    row = VX[idx]
    if w <= _X[0]: return row[0]
    for j in range(1, NX):
        if w <= _X[j]:
            x0 = _X[j - 1]; x1 = _X[j]; t = (w - x0) / (x1 - x0)
            return row[j - 1] + (row[j] - row[j - 1]) * t
    return row[-1]

def _straight_high(mask):
    for hi in range(12, 3, -1):
        m = 0x1F << (hi - 4)
        if mask & m == m: return hi
    if mask & 0x100F == 0x100F: return 3
    return -1

def ev(cards):
    rc = [0] * 13; sc = [0] * 4
    for c in cards: rc[c >> 2] += 1; sc[c & 3] += 1
    for s in range(4):
        if sc[s] >= 5:
            mask = 0
            for c in cards:
                if c & 3 == s: mask |= 1 << (c >> 2)
            st = _straight_high(mask)
            if st >= 0: return (8 << 20) | st
            ks = [r for r in range(12, -1, -1) if mask >> r & 1][:5]
            return (5 << 20) | (ks[0] << 16) | (ks[1] << 12) | (ks[2] << 8) | (ks[3] << 4) | ks[4]
    mask = 0; quads = []; trips = []; pairs = []; singles = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n:
            mask |= 1 << r
            if n == 4: quads.append(r)
            elif n == 3: trips.append(r)
            elif n == 2: pairs.append(r)
            else: singles.append(r)
    if quads:
        k = max([r for r in range(13) if rc[r] and r != quads[0]] + [0])
        return (7 << 20) | (quads[0] << 16) | (k << 12)
    if trips and (len(trips) > 1 or pairs):
        p = max(trips[1] if len(trips) > 1 else -1, pairs[0] if pairs else -1)
        return (6 << 20) | (trips[0] << 16) | (p << 12)
    st = _straight_high(mask)
    if st >= 0: return (4 << 20) | st
    singles += [0, 0, 0, 0, 0]
    if trips:
        return (3 << 20) | (trips[0] << 16) | (singles[0] << 12) | (singles[1] << 8)
    if len(pairs) >= 2:
        k = max(singles[0], pairs[2] if len(pairs) > 2 else 0)
        return (2 << 20) | (pairs[0] << 16) | (pairs[1] << 12) | (k << 8)
    if pairs:
        return (1 << 20) | (pairs[0] << 16) | (singles[0] << 12) | (singles[1] << 8) | (singles[2] << 4)
    return (singles[0] << 16) | (singles[1] << 12) | (singles[2] << 8) | (singles[3] << 4) | singles[4]


def _int(x, d=0):
    try:
        if x is None: return d
        return int(x)
    except Exception:
        return d


class Bot(_Agent):
    P_PUSH = 8.0; P_OPEN = 1.3; P_CBET = 0.6; P_MARGIN = 0.01; P_SHOVE_M = 0.003; P_CALLC = 0.8
    P_VALUE = 0.70; P_COMMIT = 16; P_STATION = 1; P_TAU = 0.0; P_MULTI = 0; P_TEX = 0; P_STR = 0; P_BUSTFIX = 1.0; P_SHOVEMODEL = 0
    def __init__(self):
        self.rng = _random.Random(0x5EED)
        self.pay = [10, 7, 5, 4, 3, 2, 1, 0]; self.cap = 200
        self._set_pay()
        self.reset_table()

    # ---------------- table lifecycle
    def reset_table(self):
        self.seen = {}; self.vpip = {}; self.raised = {}; self.shoves = {}
        self.cur_hand = None; self.cur_hist = None; self.cur_bb = 20
        self.pf_aggr = False; self.last_hand = None; self.tau_now = 0.0

    def _set_pay(self):
        p = self.pay; n = len(p)
        d = [p[k] - (p[k + 1] if k + 1 < n else 0) for k in range(n)]
        base = d[3] if n > 3 else 1
        self.base = float(base) if base > 0 else 1.0
        self.d1x = d[0] - self.base if n > 0 else 0.0
        self.d2x = d[1] - self.base if n > 1 else 0.0

    def new_table(self, rules, seat, n_players):
        try:
            self.reset_table()
            self.cap = 200
            if isinstance(rules, dict):
                hc = rules.get('hand_cap') or rules.get('max_hands') or rules.get('hands')
                if isinstance(hc, int) and 10 <= hc <= 100000: self.cap = hc
                for k in ('payouts', 'points', 'payout', 'finish_points', 'place_points'):
                    v = rules.get(k)
                    if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(t, (int, float)) for t in v):
                        self.pay = list(v); self._set_pay(); break
        except Exception:
            pass

    def hand_end(self, result):
        try:
            if isinstance(result, dict):
                h = result.get('history') or result.get('actions')
                if isinstance(h, (list, tuple)) and len(h) >= len(self.cur_hist or ()):
                    self.cur_hist = list(h)
            self._finalize()
        except Exception:
            pass

    def _finalize(self):
        h = self.cur_hist
        self.cur_hist = None
        if not h: return
        bb = self.cur_bb or 20
        did = {}
        for e in h:
            try:
                s, a = e[0], e[1]
                if not isinstance(s, int) or not isinstance(a, (tuple, list)) or len(a) < 1: continue
                k = a[0]; amt = _int(a[1] if len(a) > 1 else 0)
                f = did.setdefault(s, [0, 0, 0])
                if k in ('call', 'raise'): f[0] = 1
                if k == 'raise': f[1] = 1
                if k == 'raise' and amt >= 8 * bb: f[2] = 1
            except Exception:
                continue
        for s, f in did.items():
            self.seen[s] = self.seen.get(s, 0) + 1
            self.vpip[s] = self.vpip.get(s, 0) + f[0]
            self.raised[s] = self.raised.get(s, 0) + f[1]
            self.shoves[s] = self.shoves.get(s, 0) + f[2]

    # ---------------- opponent model helpers
    def aggr(self, s):
        n = self.seen.get(s, 0)
        return (0.15 * 4 + self.raised.get(s, 0)) / (4.0 + n)

    def loose(self, s):
        n = self.seen.get(s, 0)
        return (0.25 * 4 + self.vpip.get(s, 0)) / (4.0 + n)

    def is_folder(self, s):
        n = self.seen.get(s, 0)
        return n >= 6 and self.vpip.get(s, 0) == 0

    # ---------------- ICM
    def icm(self, st, i, alive0=None):
        si = st[i]
        if si <= 0:
            # busting now: we still hold P(top2)=1 if exactly one other player remains (heads-up)
            m = 0
            for j, x in enumerate(st):
                if j != i and x > 0: m += 1
            return self.d2x if m == 1 else 0.0
        S = 0.0
        for x in st:
            if x > 0: S += x
        e = 0.0; p2 = 0.0
        for j, sj in enumerate(st):
            if j != i and sj > 0:
                e += si / (si + sj)
                if S - sj > 0: p2 += (sj / S) * (si / (S - sj))
        if alive0 and self.P_BUSTFIX:
            for j in alive0:
                if j != i and st[j] <= 0: e += self.P_BUSTFIX   # busted in this outcome: outlasted by us
        p1 = si / S
        v = self.base * e + self.d1x * p1 + self.d2x * (p1 + p2)
        tau = self.tau_now
        if tau:
            m = 0
            for x in st:
                if x > 0: m += 1
            tot = self.base * m * (m - 1) / 2.0 + self.d1x + 2 * self.d2x
            v = (1 - tau) * v + tau * tot * si / S
        return v

    # ---------------- main entry
    def act(self, obs):
        legal = None
        try:
            legal = obs.legal
            legal = set(legal) if legal is not None else set()
        except Exception:
            legal = set()
        try:
            a = self._act(obs, legal)
            return self._legalize(a, obs, legal)
        except Exception:
            return self._safe(legal)

    def _safe(self, legal):
        if 'check' in legal: return ('check', 0)
        if 'fold' in legal: return ('fold', 0)
        if 'call' in legal: return ('call', 0)
        for k in legal:
            if k != 'raise': return (k, 0)
        return ('fold', 0)

    def _legalize(self, a, obs, legal):
        try:
            k = a[0]
            if k == 'raise':
                if 'raise' not in legal: k = 'call'
                else:
                    lo = _int(obs.min_raise); hi = _int(obs.max_raise)
                    if lo > hi: lo, hi = hi, lo
                    if hi <= 0:
                        k = 'call' if 'call' in legal else 'check'
                        return (k, 0) if k in legal else self._safe(legal)
                    amt = _int(a[1], lo)
                    if amt < lo: amt = lo
                    if amt > hi: amt = hi
                    return ('raise', int(amt))
            if k == 'fold' and 'check' in legal: return ('check', 0)
            if k == 'call' and 'call' not in legal:
                return ('check', 0) if 'check' in legal else self._safe(legal)
            if k == 'check' and 'check' not in legal:
                return self._safe(legal)
            if k in legal: return (k, 0)
            return self._safe(legal)
        except Exception:
            return self._safe(legal)

    def _act(self, o, legal):
        hole = o.hole; board = o.board or ()
        hole = [int(c) for c in hole][:2]
        board = [int(c) for c in board][:5]
        for c in hole + board:
            if c < 0 or c > 51: return self._safe(legal)
        if len(hole) != 2: return self._safe(legal)
        stacks = [max(0, _int(x)) for x in (o.stacks or [])]
        n = len(stacks)
        me = _int(o.seat, -1)
        if n == 0 or me < 0 or me >= n: return self._safe(legal)
        bets = o.bets
        bets = [max(0, _int(x)) for x in bets] if bets is not None else [0] * n
        bets = (bets + [0] * n)[:n]
        inh = o.in_hand
        if inh is None: inh = [s > 0 for s in stacks]
        inh = [bool(x) for x in inh]
        inh = (inh + [False] * n)[:n]; inh[me] = True
        bl = o.blinds
        try: sb, bb = _int(bl[0], 10), _int(bl[1], 20)
        except Exception: sb, bb = 10, 20
        if bb <= 0: bb = max(1, 2 * sb, 20)
        pot = max(0, _int(o.pot))
        to_call = max(0, _int(o.to_call))
        hand_no = o.hand_no
        hist = o.history if isinstance(o.history, (list, tuple)) else []
        street = _int(o.street, -1)
        if street not in (0, 1, 2, 3): street = {0: 0, 3: 1, 4: 2, 5: 3}.get(len(board), 0)
        # hand bookkeeping
        if hand_no is not None and hand_no != self.cur_hand:
            if self.cur_hist: self._finalize()
            self.cur_hand = hand_no; self.pf_aggr = False
        self.cur_bb = bb
        if hist: self.cur_hist = list(hist)
        hn = _int(hand_no, 100)
        self.tau_now = self.P_TAU * max(0.0, min(1.0, (self.cap - hn) / 120.0))
        st = dict(hole=hole, board=board, stacks=stacks, n=n, me=me, bets=bets, inh=inh, sb=sb, bb=bb,
                  pot=pot, to_call=to_call, street=street, hist=hist, legal=legal,
                  button=_int(o.button, 0) % n, lo=_int(o.min_raise), hi=_int(o.max_raise))
        if st['lo'] > st['hi']: st['lo'], st['hi'] = st['hi'], st['lo']
        if street == 0:
            a = self.preflop(st)
        else:
            a = self.postflop(st)
        if a[0] == 'raise' and street == 0: self.pf_aggr = True
        return a

    # ---------------- outcome stacks for ICM
    def _ev_allin(self, st, opp, eq):
        """ICM EV of going to showdown all-in vs seat opp with equity eq; returns (ev_showdown, ev_steal)."""
        stacks = st['stacks']; bets = st['bets']; me = st['me']
        mt = stacks[me] + bets[me]; ot = stacks[opp] + bets[opp]
        risk = min(mt, ot)
        dead = st['pot'] + sum(bets) - bets[me] - bets[opp]
        base = [stacks[i] for i in range(st['n'])]
        w = list(base); w[me] = mt + dead + risk; w[opp] = ot - risk
        l = list(base); l[me] = mt - risk; l[opp] = ot + dead + risk
        a0 = [i for i in range(st['n']) if stacks[i] + bets[i] > 0]
        return eq * self.icm(w, me, a0) + (1 - eq) * self.icm(l, me, a0)

    def _ev_fold(self, st):
        stacks = st['stacks']; bets = st['bets']; me = st['me']
        f = list(stacks)
        mid = st['pot'] + sum(bets)
        j = max(range(st['n']), key=lambda i: (bets[i] if i != me else -1, stacks[i]))
        f[j] += mid
        return self.icm(f, me)

    def _ev_steal(self, st):
        stacks = st['stacks']; bets = st['bets']; me = st['me']
        f = list(stacks); f[me] = stacks[me] + st['pot'] + sum(bets)
        return self.icm(f, me)

    # ---------------- preflop
    def _order_after(self, st):
        """seats still to act after me preflop (in_hand, chips behind), up to and incl. the big blind."""
        n = st['n']; me = st['me']; stacks = st['stacks']; bets = st['bets']; inh = st['inh']
        alive = [i for i in range(n) if stacks[i] > 0 or bets[i] > 0 or inh[i]]
        bt = st['button']
        # find blinds among alive in seat order after button
        seq = [(bt + k) % n for k in range(1, n + 1)]
        seq = [i for i in seq if i in alive]
        if len(alive) == 2:
            bbseat = [i for i in alive if i != bt][0] if bt in alive else seq[1 % len(seq)]
        else:
            bbseat = seq[1 % len(seq)] if seq else me
        out = []
        if me == bbseat: return out, bbseat
        k = me
        for _ in range(n):
            k = (k + 1) % n
            if inh[k] and stacks[k] > 0 and k != me: out.append(k)
            if k == bbseat: break
        return out, bbseat

    def preflop(self, st):
        hole = st['hole']; r1, r2 = hole[0] >> 2, hole[1] >> 2
        suited = (hole[0] & 3) == (hole[1] & 3)
        hi, lo = max(r1, r2), min(r1, r2)
        idx = _key(hi, lo, suited)
        pct = PCT[idx]
        stacks = st['stacks']; bets = st['bets']; me = st['me']; bb = st['bb']; n = st['n']
        inh = st['inh']; legal = st['legal']; to_call = st['to_call']
        mt = stacks[me] + bets[me]
        mx = max(bets)
        others = [i for i in range(n) if i != me and inh[i]]
        if not others: return ('check', 0) if 'check' in legal else ('call', 0)
        behind, bbseat = self._order_after(st)
        opp_max = max([stacks[i] + bets[i] for i in others] + [1])
        eff = min(mt, opp_max) / float(bb)
        # raises so far: count from bet levels + history
        nraise_h = 0
        for e in st['hist']:
            try:
                if e[1][0] == 'raise' and _int(e[1][1]) > bb: nraise_h += 1
            except Exception:
                pass
        levels = sorted(set(b for b in bets if b > bb))
        nraise = max(len(levels), nraise_h if mx > bb else 0)
        can_raise = 'raise' in legal
        alive_n = sum(1 for i in range(n) if stacks[i] > 0 or bets[i] > 0)

        if mx <= bb:  # unraised
            limpers = [i for i in others if bets[i] >= bb and i != bbseat]
            all_fold_behind = all(self.is_folder(i) for i in behind) and behind
            if eff <= self.P_PUSH or mt <= self.P_PUSH * bb:
                if can_raise and self._shove_ok(st, idx, behind, others):
                    return ('raise', st['hi'])
                if 'check' in legal: return ('check', 0)
                if all_fold_behind and can_raise: return ('raise', st['lo'])
                return ('fold', 0)
            nb = len(behind)
            if me == bbseat or nb == 0:
                if can_raise and pct <= (0.10 if limpers else 0.12):
                    return ('raise', mx + int(bb * (3 + len(limpers))))
                return ('check', 0) if 'check' in legal else ('fold', 0)
            orng = {1: 0.42, 2: 0.36, 3: 0.27, 4: 0.21, 5: 0.17, 6: 0.14}.get(nb, 0.12)
            # widen vs tight/folder fields behind, tighten vs loose callers
            lz = sum(self.loose(i) for i in behind) / len(behind)
            orng *= max(0.7, min(1.4, 1.0 + (0.25 - lz) * 1.5))
            if limpers: orng *= 0.6
            orng *= self.P_OPEN
            if all_fold_behind: orng = 1.0
            if can_raise and pct <= orng:
                size = int(bb * (2.3 if eff < 25 else 2.5)) + bb * len(limpers)
                if size >= 0.4 * mt: return ('raise', st['hi'])
                return ('raise', size)
            return ('check', 0) if 'check' in legal else ('fold', 0)

        # facing a raise
        raiser = max(others, key=lambda i: bets[i])
        r_allin = stacks[raiser] == 0
        rt = stacks[raiser] + bets[raiser]
        rbb = bets[raiser] / float(bb)
        # raiser range width estimate
        ag = self.aggr(raiser)
        if nraise <= 1:
            w0 = 0.20 if rbb <= 4 else (0.16 if rbb <= 12 else 0.12)
        elif nraise == 2: w0 = 0.06
        else: w0 = 0.035
        nseen = self.seen.get(raiser, 0)
        w = (w0 * 4 + ag * nseen * (1.0 if nraise <= 1 else 0.5)) / (4.0 + nseen) if nseen else w0
        if nseen >= 6 and ag > 0.45: w = max(w, ag * 0.9)
        if self.P_SHOVEMODEL and (r_allin or rbb >= 8) and nseen >= 3:
            srate = (self.shoves.get(raiser, 0) + 0.15) / (nseen + 3.0)
            w = max(w, srate * 0.95)
        w = max(0.025, min(1.0, w))
        eq = eq_vs(idx, w)
        # other all-in players / callers reduce our equity
        extra = [i for i in others if i != raiser and bets[i] > bb]
        for i in extra:
            e2 = eq_vs(idx, max(0.03, w * 0.8))
            eq = 1.0 / (1.0 + (1 - eq) / max(eq, 0.01) + (1 - e2) / max(e2, 0.01))
        # wake-ups behind
        nbeh = len([i for i in behind if bets[i] < mx])
        commit = to_call >= 0.35 * mt or r_allin or eff <= self.P_COMMIT or (mt - to_call) < 6 * bb
        if commit:
            ev_f = self._ev_fold(st)
            ev_c = self._ev_allin(st, raiser, eq) - 0.004 * nbeh
            # shove option when raiser not all-in: fold equity
            ev_s = -1e9
            if can_raise and not r_allin and mt > bets[raiser]:
                # raiser's continue fraction from the price he gets on our shove
                rcall = min(mt, rt) - bets[raiser]
                rfin = st['pot'] + sum(bets) - bets[me] + min(mt, rt) + rcall
                req = rcall / float(max(1, rfin))
                if req <= 0.30: k = 0.95
                elif req <= 0.38: k = 0.7
                elif req <= 0.45: k = 0.5
                else: k = 0.38
                if nraise >= 2: k = max(k, 0.7)
                if bets[raiser] >= 0.3 * rt: k = max(k, 0.9)
                fq = 1.0 - k
                eqc = eq_vs(idx, max(0.025, w * k))
                ev_s = fq * self._ev_steal(st) + (1 - fq) * self._ev_allin(st, raiser, eqc) - 0.004 * nbeh
            if 'call' in legal and ev_c >= ev_s and ev_c > ev_f + self.P_MARGIN:
                # prefer shoving if we would call and raiser not all in and we are short
                if can_raise and not r_allin and mt < 2.0 * bets[raiser] + 6 * bb: return ('raise', st['hi'])
                return ('call', 0)
            if ev_s > ev_f + self.P_MARGIN: return ('raise', st['hi'])
            return ('check', 0) if 'check' in legal else ('fold', 0)
        # deep: 3bet / call / fold
        vth = max(0.03, w * 0.25) if nraise <= 1 else 0.022
        if can_raise and pct <= vth:
            tgt = int(mx * (3.0 if nraise <= 1 else 2.3)) + sum(bets[i] for i in extra)
            if tgt >= 0.35 * mt: return ('raise', st['hi'])
            return ('raise', tgt)
        pot_tot = st['pot'] + sum(bets)
        po = to_call / float(pot_tot + to_call)
        ip = me == st['button'] or (not behind)
        need = po + (0.06 if ip else 0.10)
        if nraise >= 2: need += 0.05
        # implied odds for pairs / suited when cheap
        imp = 0.0
        if to_call <= 0.08 * mt and (hi == lo or (suited and hi - lo <= 4)): imp = 0.06
        if 'call' in legal and eq + imp >= need and to_call <= 0.3 * mt:
            return ('call', 0)
        return ('check', 0) if 'check' in legal else ('fold', 0)

    def _shove_ok(self, st, idx, behind, others):
        stacks = st['stacks']; bets = st['bets']; me = st['me']; bb = st['bb']
        mt = stacks[me] + bets[me]
        if not behind:
            behind = [i for i in others]
        ev_f = self._ev_fold(st) if st['to_call'] > 0 else self.icm(stacks, me)
        if st['to_call'] == 0:
            ev_f = self.icm([stacks[i] for i in range(st['n'])], me)
        pnf = 1.0; tot = 0.0
        nb = len(behind)
        for kk, j in enumerate(behind):
            ot = stacks[j] + bets[j]
            risk = min(mt, ot) / float(bb)
            c = (0.10 + 1.6 / max(1.0, risk)) * self.P_CALLC
            if bets[j] >= bb: c *= 1.25  # BB defends wider
            if self.P_MULTI: c *= 1.0 / (1.0 + 0.12 * (nb - 1 - kk))  # players still behind the caller
            if self.is_folder(j): c = 0.0
            elif self.seen.get(j, 0) >= 5: c = 0.5 * c + 0.5 * min(1.0, self.loose(j) * 0.8)
            c = max(0.0, min(0.9, c))
            if c <= 0: continue
            eq = eq_vs(idx, max(0.025, c))
            tot += pnf * c * self._ev_allin(st, j, eq)
            pnf *= (1 - c)
        ev_s = pnf * self._ev_steal(st) + tot
        return ev_s > ev_f + self.P_SHOVE_M

    # ---------------- postflop
    def strength(self, hole, board):
        cards = hole + board
        sc = ev(cards); cat = sc >> 20
        r1, r2 = hole[0] >> 2, hole[1] >> 2
        if r1 < r2: r1, r2 = r2, r1
        br = sorted([c >> 2 for c in board], reverse=True)
        bset = set(br)
        bcnt = {}
        for r in br: bcnt[r] = bcnt.get(r, 0) + 1
        bsuit = [0] * 4
        for c in board: bsuit[c & 3] += 1
        mbs = max(bsuit)
        bmax = br[0]
        bpaired = max(bcnt.values()) >= 2
        bsc = ev(board) if len(board) == 5 else -1
        e = 0.15
        if len(board) == 5 and sc == bsc:
            e = 0.35 if cat >= 4 else 0.12 + 0.012 * max(0, r1 - 6)
            return e, 0
        if cat == 8: e = 0.99
        elif cat == 7:
            e = 0.97 if max(bcnt.values()) < 4 else 0.55 + 0.03 * (r1 - 8)
        elif cat == 6:
            trips_b = max(bcnt.values()) >= 3
            e = 0.93 if not trips_b or r1 == r2 or r1 in bset or r2 in bset else 0.55
        elif cat == 5:
            fs = bsuit.index(mbs)
            hs = [c >> 2 for c in hole if c & 3 == fs]
            if not hs: e = 0.4
            else:
                e = 0.80 + 0.015 * (max(hs) - 6)
                if bpaired: e -= 0.10
                if mbs >= 4 and len(hs) == 1 and max(hs) < 11: e -= 0.08
        elif cat == 4:
            e = 0.84
            if mbs >= 3: e -= 0.14 if mbs == 3 else 0.30
            if bpaired: e -= 0.08
        elif cat == 3:
            if r1 == r2 and r1 in bset: e = 0.90
            elif r1 in bset and bcnt.get(r1, 0) >= 2 or r2 in bset and bcnt.get(r2, 0) >= 2:
                k = r2 if (r1 in bset and bcnt.get(r1, 0) >= 2) else r1
                e = 0.76 + 0.008 * (k - 6)
            else: e = 0.3
            if mbs >= 3: e -= 0.10
        elif cat == 2:
            if r1 != r2 and r1 in bset and r2 in bset:
                e = 0.82 if not bpaired else 0.66
                if mbs >= 3: e -= 0.08
            else:
                e = self._pair_e(r1, r2, br, bset, bcnt, bmax)
        elif cat == 1:
            e = self._pair_e(r1, r2, br, bset, bcnt, bmax)
        else:
            e = None
        if e is None:
            e = 0.10 + 0.012 * max(0, r1 - 6)
        if self.P_TEX and cat <= 2:
            if mbs >= 4: e -= 0.15
            elif mbs == 3: e -= 0.06
        # draws
        draw = 0
        if len(board) < 5 and cat < 5:
            outs = 0
            allc = hole + board
            su = [0] * 4
            for c in allc: su[c & 3] += 1
            for s in range(4):
                if su[s] == 4 and ((hole[0] & 3) == s or (hole[1] & 3) == s):
                    outs += 9 if max([c >> 2 for c in hole if c & 3 == s]) >= 9 or bsuit[s] <= 2 else 6
            if cat < 4:
                mask = 0
                for c in allc: mask |= 1 << (c >> 2)
                bm = 0
                for r in br: bm |= 1 << r
                k = 0
                for x in range(13):
                    if not mask >> x & 1:
                        if _straight_high(mask | 1 << x) >= 0 and _straight_high(bm | 1 << x) < 0: k += 1
                outs += 4 * min(k, 2) - (1 if outs >= 9 and k else 0)
            if cat == 0 and r2 > bmax: outs += 3
            if outs:
                draw = outs
                de = 1 - (1 - outs / 47.0) ** (2 if len(board) == 3 else 1)
                e = e + (1 - e) * de * 0.9
        return max(0.02, min(0.99, e)), draw

    def _pair_e(self, r1, r2, br, bset, bcnt, bmax):
        if r1 == r2:
            if r1 > bmax: return 0.74 + 0.01 * (r1 - 8)
            k = sum(1 for r in bset if r > r1)
            return max(0.22, 0.52 - 0.11 * k)
        pr = -1; kick = -1
        if r1 in bset and bcnt[r1] == 1: pr, kick = r1, r2
        elif r2 in bset and bcnt[r2] == 1: pr, kick = r2, r1
        if pr < 0:
            return 0.10 + 0.012 * max(0, r1 - 6)
        ranks = sorted(bset, reverse=True)
        pos = ranks.index(pr)
        if pos == 0: return 0.60 + 0.01 * (kick - 6)
        if pos == 1: return 0.47 + 0.008 * (kick - 6)
        return 0.37 + 0.005 * (kick - 6)

    def postflop(self, st):
        hole = st['hole']; board = st['board']; stacks = st['stacks']; bets = st['bets']; me = st['me']
        inh = st['inh']; legal = st['legal']; to_call = st['to_call']; n = st['n']; bb = st['bb']
        e, draw = self.strength(hole, board)
        opps = [i for i in range(n) if i != me and inh[i]]
        nop = max(1, len(opps))
        em = e ** (1 + 0.75 * (nop - 1))
        mt = stacks[me] + bets[me]
        mx = max(bets)
        pot_tot = st['pot'] + sum(bets)
        can_raise = 'raise' in legal
        live = [i for i in opps if stacks[i] > 0]
        r = self.rng.random()
        if to_call == 0:
            if not can_raise or not live: return ('check', 0)
            spr = stacks[me] / float(max(1, pot_tot))
            if self.P_STATION and nop == 1 and self.seen.get(opps[0], 0) >= 6 and self.loose(opps[0]) > 0.55 and self.aggr(opps[0]) < 0.2:
                # calling station: thin value, no bluffs
                if em >= 0.80 and spr <= 2.0: return ('raise', st['hi'])
                if em >= 0.56: return ('raise', bets[me] + int((0.75 if em >= 0.7 else 0.5) * pot_tot))
                return ('check', 0)
            if em >= self.P_VALUE:
                if spr <= 1.3: return ('raise', st['hi'])
                return ('raise', bets[me] + int(0.66 * pot_tot))
            if st['street'] == 3 and nop == 1 and em >= 0.58 and r < 0.6:
                return ('raise', bets[me] + int(0.45 * pot_tot))
            if nop == 1 and self.pf_aggr and st['street'] == 1 and r < self.P_CBET:
                return ('raise', bets[me] + int(0.5 * pot_tot))
            if nop <= 2 and draw >= 8 and st['street'] < 3 and r < 0.5:
                return ('raise', bets[me] + int(0.6 * pot_tot))
            if nop == 1 and self.pf_aggr and st['street'] == 2 and (em >= 0.5 or draw >= 8) and r < 0.4:
                return ('raise', bets[me] + int(0.55 * pot_tot))
            return ('check', 0)
        # facing a bet
        bettor = max(opps, key=lambda i: bets[i]) if opps else me
        prior = max(1, pot_tot - to_call)
        ratio = min(1.5, to_call / float(prior))
        mania = min(1.0, max(0.0, (self.aggr(bettor) - 0.2) / 0.4))
        ex = 0.55 * ratio * (1 - 0.6 * mania)
        if bets[me] > 0: ex = ex * 1.6 + 0.35   # they raised our bet: much stronger range
        if self.P_STR: ex += 0.2 * (st['street'] - 1)  # turn/river bets are stronger
        ee = em ** (1 + ex)
        po = to_call / float(pot_tot + to_call)
        big = to_call >= 0.3 * mt or stacks[me] - to_call < 4 * bb
        if ee >= 0.78 and can_raise and live:
            tgt = mx + int(0.85 * (pot_tot + to_call))
            if tgt >= 0.4 * mt: tgt = st['hi']
            return ('raise', tgt)
        if 'call' not in legal: return ('check', 0) if 'check' in legal else ('fold', 0)
        if big:
            ev_f = self._ev_fold(st)
            ev_c = self._ev_allin(st, bettor, ee)
            if ev_c > ev_f: return ('call', 0)
            return ('fold', 0)
        if ee >= po + 0.04: return ('call', 0)
        return ('fold', 0)
